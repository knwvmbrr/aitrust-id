"""Verifier-only outcome/refusal controls; no privileged operations or network."""
import errno
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch,Mock
s=importlib.util.spec_from_file_location('isolation',Path(__file__).with_name('verify-isolation.py'));v=importlib.util.module_from_spec(s);s.loader.exec_module(v)
class Isolation(unittest.TestCase):
    def test_only_permission_or_bounded_timeout_is_candidate_denial(self):
        self.assertEqual(v.denial_mode(TimeoutError()),'bounded_timeout')
        for n in [errno.EPERM,errno.EACCES]:self.assertEqual(v.denial_mode(PermissionError(n,'PRIVATE_SYNTHETIC_CANARY')),'permission_denied')
        for n in [errno.ECONNREFUSED,errno.ENETUNREACH,errno.EHOSTUNREACH,errno.EINTR,errno.EIO]:self.assertIsNone(v.denial_mode(OSError(n,'PRIVATE_SYNTHETIC_CANARY')))
        self.assertIsNone(v.denial_mode(ValueError('private')))
    def test_closed_functional_record_needs_all_actual_boolean_controls(self):
        r={n:True for n in ['root_home_blocked','operator_home_blocked','source_write_blocked','loopback_connects','nonloopback_connect_blocked']};r['nonloopback_denial_mode']='bounded_timeout'
        self.assertTrue(v.valid_functional(r,True,True));self.assertFalse(v.valid_functional(r,False,True));self.assertFalse(v.valid_functional(r,True,False));self.assertFalse(v.valid_functional(r,1,True))
        for name in list(r):
            bad=dict(r);bad[name]=False if name!='nonloopback_denial_mode'else'unknown';self.assertFalse(v.valid_functional(bad,True,True))
        bad=dict(r);bad['raw_input']='private';self.assertFalse(v.valid_functional(bad,True,True))
        bad=dict(r);bad['loopback_connects']=1;self.assertFalse(v.valid_functional(bad,True,True))
    def test_outside_control_targets_only_approved_own_TCP22_with_finite_budget(self):
        connection=Mock()
        with patch.object(v.socket,'create_connection',return_value=connection)as connect:
            self.assertTrue(v.owned_target_ready('192.0.2.1'));connect.assert_called_once_with(('192.0.2.1',22),timeout=2);connection.close.assert_called_once()
        with patch.object(v.socket,'create_connection',side_effect=TimeoutError()):self.assertFalse(v.owned_target_ready('192.0.2.1'))
if __name__=='__main__':unittest.main()
