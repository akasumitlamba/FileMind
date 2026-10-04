"""Small, typed Windows API boundary. No shell command interpolation."""
import ctypes as C
from ctypes import wintypes as W
import os
import sys
import uuid
import winreg
from pathlib import Path


class CREDENTIAL(C.Structure):
    _fields_ = [("Flags", W.DWORD), ("Type", W.DWORD), ("TargetName", W.LPWSTR),
                ("Comment", W.LPWSTR), ("LastWritten", W.FILETIME), ("CredentialBlobSize", W.DWORD),
                ("CredentialBlob", C.POINTER(C.c_ubyte)), ("Persist", W.DWORD),
                ("AttributeCount", W.DWORD), ("Attributes", C.c_void_p),
                ("TargetAlias", W.LPWSTR), ("UserName", W.LPWSTR)]


class Vault:
    def __init__(self, namespace="GROK"):
        self.namespace = namespace
        self.api = C.WinDLL("advapi32", use_last_error=True)
        self.api.CredWriteW.argtypes = [C.POINTER(CREDENTIAL), W.DWORD]
        self.api.CredReadW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, C.POINTER(C.POINTER(CREDENTIAL))]
        self.api.CredDeleteW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD]
        self.api.CredFree.argtypes = [C.c_void_p]

    def put(self, provider, secret):
        raw = secret.encode("utf-16-le")
        if not raw or len(raw) > 2560:
            raise ValueError("Enter a valid API key (maximum 1280 characters).")
        blob = (C.c_ubyte * len(raw)).from_buffer_copy(raw)
        cred = CREDENTIAL(Type=1, TargetName=f"{self.namespace}/{provider}", CredentialBlobSize=len(raw),
                          CredentialBlob=blob, Persist=2, UserName="API key")
        if not self.api.CredWriteW(C.byref(cred), 0):
            raise ValueError("Windows Credential Manager could not save the key.")

    def get(self, provider):
        ptr = C.POINTER(CREDENTIAL)()
        if not self.api.CredReadW(f"{self.namespace}/{provider}", 1, 0, C.byref(ptr)):
            if C.get_last_error() == 1168:
                return None
            raise ValueError("Windows Credential Manager is unavailable.")
        try:
            return C.string_at(ptr.contents.CredentialBlob, ptr.contents.CredentialBlobSize).decode("utf-16-le")
        finally:
            self.api.CredFree(ptr)

    def remove(self, provider):
        if not self.api.CredDeleteW(f"{self.namespace}/{provider}", 1, 0) and C.get_last_error() != 1168:
            raise ValueError("Windows could not remove the credential.")


class SHFILEOP(C.Structure):
    _fields_ = [("hwnd", W.HWND), ("wFunc", W.UINT), ("pFrom", W.LPCWSTR),
                ("pTo", W.LPCWSTR), ("fFlags", W.WORD), ("fAnyOperationsAborted", W.BOOL),
                ("hNameMappings", C.c_void_p), ("lpszProgressTitle", W.LPCWSTR)]


def recycle(paths):
    # Windows retains its own confirmation, including permanent deletion warnings
    # for drives that cannot recycle. Never set FOF_NOCONFIRMATION.
    source = C.create_unicode_buffer("\0".join(str(Path(p).absolute()) for p in paths) + "\0\0")
    op = SHFILEOP(wFunc=3, pFrom=C.cast(source, W.LPCWSTR), fFlags=0x40 | 0x100)
    api = C.windll.shell32.SHFileOperationW
    api.argtypes = [C.POINTER(SHFILEOP)]
    result = api(C.byref(op))
    if result or op.fAnyOperationsAborted:
        raise ValueError("Delete was canceled or Windows could not recycle every item. Refresh before retrying.")


class SHELLEXECUTE(C.Structure):
    _fields_ = [("cbSize", W.DWORD), ("fMask", C.c_ulong), ("hwnd", W.HWND),
                ("lpVerb", W.LPCWSTR), ("lpFile", W.LPCWSTR), ("lpParameters", W.LPCWSTR),
                ("lpDirectory", W.LPCWSTR), ("nShow", C.c_int), ("hInstApp", W.HINSTANCE),
                ("lpIDList", C.c_void_p), ("lpClass", W.LPCWSTR), ("hkeyClass", W.HKEY),
                ("dwHotKey", W.DWORD), ("hIcon", W.HANDLE), ("hProcess", W.HANDLE)]


def properties(path, hwnd=0):
    info = SHELLEXECUTE(cbSize=C.sizeof(SHELLEXECUTE), fMask=0xC, hwnd=hwnd,
                       lpVerb="properties", lpFile=str(path), nShow=1)
    if not C.windll.shell32.ShellExecuteExW(C.byref(info)):
        raise ValueError("Windows could not open properties for this item.")


class OPENAS(C.Structure):
    _fields_ = [("pcszFile", W.LPCWSTR), ("pcszClass", W.LPCWSTR), ("oaifInFlags", C.c_int)]


def open_with(path, hwnd=0):
    info = OPENAS(str(path), None, 4)
    C.windll.shell32.SHOpenWithDialog(W.HWND(hwnd), C.byref(info))


def known_folder(identifier, fallback):
    guid = (C.c_ubyte * 16).from_buffer_copy(uuid.UUID(identifier).bytes_le)
    ptr = W.LPWSTR()
    if C.windll.shell32.SHGetKnownFolderPath(C.byref(guid), 0, None, C.byref(ptr)) == 0:
        try:
            return ptr.value
        finally:
            C.windll.ole32.CoTaskMemFree(C.cast(ptr, C.c_void_p))
    return str(Path.home() / fallback)


def locations():
    return {
        "Home": str(Path.home()),
        "Desktop": known_folder("B4BFCC3A-DB2C-424C-B029-7FE99A87C641", "Desktop"),
        "Documents": known_folder("FDD39AD0-238F-46AF-ADB4-6C85480369C7", "Documents"),
        "Downloads": known_folder("374DE290-123F-4565-9164-39C4925E467B", "Downloads"),
        "Pictures": known_folder("33E28130-4E1E-4676-835A-98395C3BC3BB", "Pictures"),
        "Music": known_folder("4BD8D571-6D19-48D3-BE97-422220080E43", "Music"),
        "Videos": known_folder("18989B1D-99B5-455B-841C-AB7C74E4DDFC", "Videos"),
    }


def startup(enabled):
    if not getattr(sys, "frozen", False):
        if enabled:
            raise ValueError("Start with Windows is available in the packaged application.")
        return
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        if enabled:
            winreg.SetValueEx(key, "GROK", 0, winreg.REG_SZ, f'"{sys.executable}" --minimized')
        else:
            try:
                winreg.DeleteValue(key, "GROK")
            except FileNotFoundError:
                pass


def register_hotkey(hwnd, shortcut):
    C.windll.user32.UnregisterHotKey(W.HWND(hwnd), 71)
    parts = shortcut.upper().split("+")
    mods = 0x4000
    for part in parts[:-1]:
        if part not in {"CTRL", "ALT", "SHIFT"}:
            raise ValueError("Shortcut must use Ctrl, Alt or Shift plus one letter.")
        mods |= {"CTRL": 2, "ALT": 1, "SHIFT": 4}[part]
    if len(parts) < 2 or len(parts[-1]) != 1 or not parts[-1].isascii() or not parts[-1].isalnum():
        raise ValueError("Use a shortcut such as Ctrl+Alt+G.")
    if not C.windll.user32.RegisterHotKey(W.HWND(hwnd), 71, mods, ord(parts[-1])):
        raise ValueError("That global shortcut is in use by another app. Choose another in Settings.")
