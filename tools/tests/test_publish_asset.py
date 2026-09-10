import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import publish_asset


class AssetTests(unittest.TestCase):
    def test_upload_verified_before_draft_is_published(self):
        manifest=dict(release_tag='app-test',version='test',notes='Reviewed notes',
                      files={'TechLoungeTweaks/TechLoungeTweaks.zip':'a'*64})
        with tempfile.TemporaryDirectory() as temp:
            archive=Path(temp)/'TechLoungeTweaks.zip';archive.write_bytes(b'fixture')
            with patch.object(publish_asset,'token',return_value='fixture'), patch.object(publish_asset.subprocess,'check_output',return_value='commit'), patch.object(publish_asset,'request',side_effect=[None,{'id':1,'draft':True},[],{'digest':'sha256:'+'a'*64},{}]) as request:
                publish_asset.publish(Path(temp),manifest,archive)
                self.assertEqual([c.args[1] for c in request.call_args_list],['GET','POST','GET','POST','PATCH'])
                self.assertEqual(request.call_args_list[1].args[3]['draft'],True)
            with patch.object(publish_asset,'token',return_value='fixture'), patch.object(publish_asset,'request',side_effect=[{'id':1,'draft':True},[{'name':archive.name,'digest':'wrong'}]]) as request:
                with self.assertRaises(RuntimeError):publish_asset.publish(Path(temp),manifest,archive)
                self.assertFalse(any(c.args[1]=='PATCH' for c in request.call_args_list))
            with patch.object(publish_asset,'token',return_value='fixture'), patch.object(publish_asset,'request',side_effect=[{'id':1,'draft':True},[{'id':7,'name':archive.name,'state':'starter'}],None,{'digest':'sha256:'+'a'*64},{}]) as request:
                publish_asset.publish(Path(temp),manifest,archive)
                self.assertEqual([c.args[1] for c in request.call_args_list],['GET','GET','DELETE','POST','PATCH'])
