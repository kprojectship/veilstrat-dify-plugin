import importlib
import json
import unittest
from unittest.mock import Mock, patch
import httpx
from dify_plugin.entities.tool import ToolRuntime
from common.client import VeilStratClient, VeilStratError
from provider.veilstrat import VeilstratProvider

REAL_CLIENT = httpx.Client
TEST_KEY = 'not-a-real-api-key'
UUID = '4066c846-48ea-403a-97b1-fd60503fdb97'

class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.status = 200
        self.payload = {'companies': [{'id': UUID, 'name': 'Example Co'}], 'page': 1, 'total': 1}
        self.headers = {}
        def handle(request):
            self.calls.append(request)
            return httpx.Response(self.status, json=self.payload, headers=self.headers)
        self.transport = httpx.MockTransport(handle)
        def client(**kwargs):
            return REAL_CLIENT(transport=self.transport, **kwargs)
        self.patcher = patch('common.client.httpx.Client', side_effect=client)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.client = VeilStratClient(TEST_KEY)

    def test_full_sdk_registration_loads_all_provider_and_tool_metadata(self):
        from dify_plugin import DifyPluginEnv
        from dify_plugin.core.plugin_registration import PluginRegistration
        registration = PluginRegistration(DifyPluginEnv())
        self.assertEqual(set(registration.tools_mapping['veilstrat'][2]), {'search_companies','get_company','search_slices','get_filters','get_usage','get_health'})

    def test_company_search_matches_documented_contract(self):
        result=self.client.invoke('search_companies',{'signal_query':' signal:hiring:30d ','countries':'us, GB,us','page':1,'page_size':10})
        request=self.calls[0]
        self.assertEqual(request.method,'POST')
        self.assertEqual(str(request.url),'https://app.veilstrat.com/api/v1/companies')
        self.assertEqual(json.loads(request.content),{'signal_query':'signal:hiring:30d','countries':['US','GB'],'page':1,'pageSize':10})
        self.assertEqual(request.headers['authorization'],'Bearer '+TEST_KEY)
        self.assertEqual(result['companies'][0]['name'],'Example Co')
        self.assertEqual(result['page'],1)
        self.assertEqual(len(self.calls),1)

    def test_all_six_actual_sdk_tools_produce_json(self):
        cases=[('search_companies',{'signal_query':'signal:hiring:30d'},'/companies'),('get_company',{'company_id':UUID},'/companies/'+UUID),('search_slices',{'slice':'ai-sdr-hiring','countries':'US','score_min':70},'/slices'),('get_filters',{},'/filters'),('get_usage',{},'/stats'),('get_health',{},'/health')]
        for operation,parameters,path in cases:
            with self.subTest(operation=operation):
                module=importlib.import_module('tools.'+operation)
                tool_class=getattr(module,''.join(w.title() for w in operation.split('_'))+'Tool')
                tool=tool_class(runtime=ToolRuntime(credentials={'api_key':TEST_KEY},user_id=None,session_id=None),session=Mock())
                messages=list(tool._invoke(parameters))
                self.assertEqual(len(messages),1)
                self.assertEqual(messages[0].type.value,'json')
                self.assertEqual(self.calls[-1].url.path,'/api/v1'+path)
                self.assertEqual(messages[0].message.json_object,self.payload)

    def test_slice_query_and_zero_score_are_preserved(self):
        self.client.invoke('search_slices',{'slice':'ai-sdr-hiring','countries':'us,gb','score_min':0})
        self.assertEqual(dict(self.calls[0].url.params),{'slice':'ai-sdr-hiring','countries':'US,GB','scoreMin':'0'})

    def test_dossier_normalizes_uuid_and_never_accepts_a_url(self):
        self.client.invoke('get_company',{'company_id':' '+UUID.upper()+' '})
        self.assertTrue(str(self.calls[0].url).endswith(UUID))
        with self.assertRaisesRegex(VeilStratError,'UUID'):
            self.client.invoke('get_company',{'company_id':'https://example.org/'})
        self.assertEqual(len(self.calls),1)

    def test_invalid_inputs_do_not_make_requests(self):
        for operation,values in [('search_companies',{'signal_query':''}),('search_companies',{'signal_query':'x','page_size':51}),('search_companies',{'signal_query':'x','page_size':1.5}),('search_companies',{'signal_query':'x','page_size':True}),('search_companies',{'signal_query':'x','page':11,'page_size':50}),('search_companies',{'signal_query':'x','countries':'United States'}),('search_slices',{'slice':''}),('search_slices',{'slice':'x','score_min':101}),('search_slices',{'slice':'x','score_min':float('nan')}),('other',{})]:
            with self.subTest(operation=operation,values=values):
                with self.assertRaises(VeilStratError):self.client.invoke(operation,values)
        self.assertEqual(self.calls,[])

    def test_provider_validation_uses_only_unmetered_checks(self):
        VeilstratProvider()._validate_credentials({'api_key':TEST_KEY})
        self.assertEqual([request.url.path for request in self.calls],['/api/v1/health','/api/v1/stats'])

    def test_http_errors_are_not_retried_and_never_echo_secrets(self):
        for status in [301,401,403,404,422,429,500]:
            self.status=status
            self.payload={'secret':TEST_KEY,'detail':'sensitive upstream body'}
            self.headers={'Retry-After':'60','Location':'https://untrusted.example/'}
            before=len(self.calls)
            with self.subTest(status=status):
                with self.assertRaises(VeilStratError) as caught:self.client.invoke('get_usage',{})
                self.assertNotIn(TEST_KEY,str(caught.exception))
                self.assertNotIn('sensitive upstream body',str(caught.exception))
                self.assertEqual(len(self.calls),before+1)
                if status==429:self.assertIn('60 seconds',str(caught.exception))

    def test_both_documented_response_envelopes_remain_intact(self):
        for payload in [{'data':[{'id':UUID}],'pagination':{'page':1}},{'companies':[{'id':UUID}],'page':1,'total':1}]:
            self.payload=payload
            self.assertEqual(self.client.invoke('search_companies',{'signal_query':'signal:hiring:30d'}),payload)

    def test_arbitrary_destination_is_rejected(self):
        with self.assertRaisesRegex(VeilStratError,'Unsupported'):
            self.client.request('GET','https://untrusted.example/')
        self.assertEqual(self.calls,[])

    def test_network_error_is_sanitized_and_not_retried(self):
        with patch('common.client.httpx.Client',side_effect=httpx.ConnectError(TEST_KEY)) as request:
            with self.assertRaisesRegex(VeilStratError,'No automatic retry') as caught:
                self.client.invoke('get_health',{})
            self.assertNotIn(TEST_KEY,str(caught.exception))
            self.assertEqual(request.call_count,1)

    def test_invalid_keys_rejected_before_transport(self):
        for key in ['',None,'with whitespace','key\nheader']:
            with self.assertRaises(VeilStratError):VeilStratClient(key)
        self.assertEqual(self.calls,[])

if __name__=='__main__':unittest.main()
