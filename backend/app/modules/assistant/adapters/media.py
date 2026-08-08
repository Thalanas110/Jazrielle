import ctypes
from typing import Protocol


class MediaAdapter(Protocol):
    def play(self) -> None: ...

    def pause(self) -> None: ...

    def set_volume(self, percent: int) -> None: ...


class WindowsMediaAdapter:
    _MEDIA_PLAY_PAUSE = 0xB3

    def play(self) -> None:
        self._send_media_key()

    def pause(self) -> None:
        self._send_media_key()

    def set_volume(self, percent: int) -> None:
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        except ImportError as error:
            raise RuntimeError("Windows audio controls are not installed.") from error

        device = AudioUtilities.GetSpeakers()
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(percent / 100, None)

    def _send_media_key(self) -> None:
        ctypes.windll.user32.keybd_event(self._MEDIA_PLAY_PAUSE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(self._MEDIA_PLAY_PAUSE, 0, 2, 0)
