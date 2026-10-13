"""Native NTFS proof of the installer root's explicit inheritable user grant."""

import ctypes
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(sys.platform == "win32", "Windows token identity and NTFS ACLs required")
class WindowsInstallerAccessTests(unittest.TestCase):
    def setUp(self):
        from clef_use.windows_observer import process_user

        self.temporary = tempfile.TemporaryDirectory(prefix="clef-installer-access-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.user = process_user(os.getpid())

    def directory(self, name, grant):
        from clef_use.windows_observer import DWORD, HANDLE, SecurityAttributes, api

        kernel, security, _ = api()
        descriptor, size = HANDLE(), DWORD()
        sddl = f"D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA){grant}"
        self.assertTrue(
            security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                sddl, 1, ctypes.byref(descriptor), ctypes.byref(size)
            )
        )
        path = self.root / name
        try:
            attributes = SecurityAttributes(ctypes.sizeof(SecurityAttributes), descriptor, False)
            self.assertTrue(kernel.CreateDirectoryW(str(path), ctypes.byref(attributes)))
        finally:
            kernel.LocalFree(descriptor)
        return path

    def ready(self, path):
        from clef_use.installer import windows_existing_user_access

        return windows_existing_user_access(path, self.user)

    def acl(self, path):
        from clef_use.windows_observer import DWORD, HANDLE, Acl, api, sid_string

        kernel, security, _ = api()
        descriptor, acl = HANDLE(), HANDLE()
        error = security.GetNamedSecurityInfoW(
            str(path), 1, 4, None, None, ctypes.byref(acl), None, ctypes.byref(descriptor)
        )
        self.assertEqual(error, 0)
        try:
            header = ctypes.cast(acl, ctypes.POINTER(Acl)).contents
            digest = hashlib.sha256(ctypes.string_at(acl, header.size)).hexdigest()
            grants = []
            for index in range(header.count):
                ace = HANDLE()
                self.assertTrue(security.GetAce(acl, index, ctypes.byref(ace)))
                if ctypes.c_ubyte.from_address(ace.value).value != 0:
                    continue
                if sid_string(ace.value + 8) == self.user:
                    grants.append(
                        (
                            ctypes.c_ubyte.from_address(ace.value + 1).value,
                            DWORD.from_address(ace.value + 4).value,
                        )
                    )
            return digest, grants
        finally:
            kernel.LocalFree(descriptor)

    def test_proven_root_survives_mutator_timeout_and_preserves_user_data(self):
        from unittest.mock import patch

        from clef_use.installer import windows_user_access

        path = self.directory("configured", f"(A;OICI;FA;;;{self.user})")
        child = path / "user.txt"
        child.write_bytes(b"Preserve existing user bytes")
        self.assertTrue(self.ready(path))
        before = (self.acl(path)[0], self.acl(child)[0])
        native_run = subprocess.run

        def unavailable_mutator(argv, *args, **kwargs):
            if Path(argv[0]).stem.casefold() == "icacls":
                raise subprocess.TimeoutExpired(argv, 15)
            return native_run(argv, *args, **kwargs)

        # Keep real identity and NTFS observation. Only fail the mutation tool:
        # an already proven root must survive, while required repair must fail.
        with patch.object(subprocess, "run", side_effect=unavailable_mutator):
            windows_user_access(path, preserve_existing=True)
            with self.assertRaises(subprocess.TimeoutExpired):
                windows_user_access(path)
        self.assertTrue(self.ready(path))
        self.assertEqual((self.acl(path)[0], self.acl(child)[0]), before)
        self.assertEqual(child.read_bytes(), b"Preserve existing user bytes")
        descendant = path / "new-directory"
        descendant.mkdir()
        new_file = descendant / "new-file.txt"
        new_file.write_bytes(b"New inherited file")
        self.assertIn((19, 0x1F01FF), self.acl(descendant)[1])
        self.assertIn((16, 0x1F01FF), self.acl(new_file)[1])

    def test_missing_user_grant_is_not_proven_and_canonical_grant_repairs_it(self):
        from clef_use.installer import windows_user_access

        path = self.directory("missing", "")
        self.assertFalse(self.ready(path))
        windows_user_access(path, preserve_existing=True)
        self.assertTrue(self.ready(path))

    def test_partial_and_self_only_grants_do_not_prove_future_child_access(self):
        for name, grant in (("partial", "(A;OICI;GR;;;{})"), ("self", "(A;;FA;;;{})")):
            with self.subTest(name=name):
                path = self.directory(name, grant.format(self.user))
                self.assertFalse(self.ready(path))

    def test_inherit_only_and_no_propagate_grants_are_not_equivalent(self):
        for name, flags in (("inherit-only", "OICIIO"), ("no-propagate", "OICINP")):
            with self.subTest(name=name):
                path = self.directory(name, f"(A;{flags};FA;;;{self.user})")
                self.assertFalse(self.ready(path))

    def test_inherited_grant_does_not_substitute_for_explicit_root_anchor(self):
        parent = self.directory("parent", f"(A;OICI;FA;;;{self.user})")
        child = parent / "inherited"
        child.mkdir()
        self.assertFalse(self.ready(child))

    def test_deny_ace_prevents_the_existing_grant_proof(self):
        path = self.directory("deny", f"(D;;GR;;;SY)(A;OICI;FA;;;{self.user})")
        self.assertFalse(self.ready(path))


if __name__ == "__main__":
    unittest.main()
