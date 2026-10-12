// SPDX-License-Identifier: GPL-3.0-only
// External WASAPI process loopback. Audio stays in the parent's memory.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <audioclientactivationparams.h>
#include <wrl.h>
#include <wrl/implements.h>
#include <cstdio>
#include <cstdint>
#include <vector>
#include <thread>
#include <stdexcept>

using Microsoft::WRL::ComPtr;
using namespace Microsoft::WRL;

void check(HRESULT result) {
    if (FAILED(result)) {
        char message[64];
        sprintf_s(message, "WASAPI HRESULT 0x%08lX", static_cast<unsigned long>(result));
        throw std::runtime_error(message);
    }
}

class Activation final : public RuntimeClass<RuntimeClassFlags<ClassicCom>, FtmBase,
                                             IActivateAudioInterfaceCompletionHandler> {
public:
    HANDLE ready = CreateEventW(nullptr, FALSE, FALSE, nullptr);
    HRESULT result = E_PENDING;
    ComPtr<IAudioClient> client;
    ~Activation() { CloseHandle(ready); }
    STDMETHOD(ActivateCompleted)(IActivateAudioInterfaceAsyncOperation* operation) override {
        ComPtr<IUnknown> audio;
        HRESULT activated = E_FAIL;
        result = operation->GetActivateResult(&activated, &audio);
        if (SUCCEEDED(result)) result = activated;
        if (SUCCEEDED(result)) result = audio.As(&client);
        SetEvent(ready);
        return S_OK;
    }
};

bool write_all(const void* source, DWORD length) {
    auto data = static_cast<const BYTE*>(source);
    HANDLE output = GetStdHandle(STD_OUTPUT_HANDLE);
    while (length) {
        DWORD written = 0;
        if (!WriteFile(output, data, length, &written, nullptr) || written == 0) return false;
        data += written; length -= written;
    }
    return true;
}

int wmain(int argc, wchar_t** argv) {
    if (argc == 2 && wcscmp(argv[1], L"--version") == 0) {
        puts("Strigoi Sonar Capture 1; process loopback; float32 48000 Hz stereo");
        return 0;
    }
    if (argc != 3 || wcscmp(argv[1], L"--pid") != 0) {
        fputs("Usage: sonar-capture --pid PROCESS_ID\n", stderr); return 2;
    }
    wchar_t* end = nullptr;
    unsigned long id = wcstoul(argv[2], &end, 10);
    if (!id || *end || id == GetCurrentProcessId()) return 2;
    HANDLE target = OpenProcess(SYNCHRONIZE, FALSE, id);
    if (!target) { fputs("Process unavailable\n", stderr); return 3; }
    HRESULT apartment = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (FAILED(apartment)) { CloseHandle(target); return 4; }
    HANDLE samples = CreateEventW(nullptr, FALSE, FALSE, nullptr);
    HANDLE stop = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    int exit_code = 0;
    try {
        auto activation = Make<Activation>();
        AUDIOCLIENT_ACTIVATION_PARAMS params = {};
        params.ActivationType = AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK;
        params.ProcessLoopbackParams.TargetProcessId = id;
        params.ProcessLoopbackParams.ProcessLoopbackMode = PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE;
        PROPVARIANT property = {};
        property.vt = VT_BLOB;
        property.blob.cbSize = sizeof(params);
        property.blob.pBlobData = reinterpret_cast<BYTE*>(&params);
        ComPtr<IActivateAudioInterfaceAsyncOperation> pending;
        check(ActivateAudioInterfaceAsync(VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK,
              __uuidof(IAudioClient), &property, activation.Get(), &pending));
        if (WaitForSingleObject(activation->ready, 10000) != WAIT_OBJECT_0)
            throw std::runtime_error("Audio activation timed out");
        check(activation->result);
        ComPtr<IAudioClient> client = activation->client;
        WAVEFORMATEX format = {};
        format.wFormatTag = WAVE_FORMAT_IEEE_FLOAT;
        format.nChannels = 2;
        format.nSamplesPerSec = 48000;
        format.wBitsPerSample = 32;
        format.nBlockAlign = 8;
        format.nAvgBytesPerSec = 48000 * 8;
        check(client->Initialize(AUDCLNT_SHAREMODE_SHARED,
              AUDCLNT_STREAMFLAGS_LOOPBACK | AUDCLNT_STREAMFLAGS_EVENTCALLBACK |
              AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM | AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY,
              0, 0, &format, nullptr));
        check(client->SetEventHandle(samples));
        ComPtr<IAudioCaptureClient> capture;
        check(client->GetService(IID_PPV_ARGS(&capture)));
        check(client->Start());
        const char magic[8] = {'S','T','R','S','A','0','0','1'};
        const uint32_t description[3] = {48000, 2, 4};
        if (!write_all(magic, sizeof(magic)) || !write_all(description, sizeof(description)))
            throw std::runtime_error("Parent pipe closed");
        // EOF on stdin is the explicit stop request. The Python parent owns this pipe.
        std::thread input([stop]() {
            BYTE command; DWORD bytes;
            ReadFile(GetStdHandle(STD_INPUT_HANDLE), &command, 1, &bytes, nullptr);
            SetEvent(stop);
        });
        HANDLE waits[3] = {stop, target, samples};
        try {
            bool connected = true;
            std::vector<BYTE> silence;
            while (connected) {
                DWORD signaled = WaitForMultipleObjects(3, waits, FALSE, 250);
                if (signaled == WAIT_OBJECT_0 || signaled == WAIT_OBJECT_0+1) break;
                if (signaled == WAIT_FAILED) throw std::runtime_error("Audio wait failed");
                UINT32 count = 0;
                check(capture->GetNextPacketSize(&count));
                if (!count) {
                    const uint32_t heartbeat[2] = {0, 0};
                    connected = write_all(heartbeat, sizeof(heartbeat));
                    continue;
                }
                while (count && connected) {
                    BYTE* audio = nullptr; DWORD flags = 0; UINT32 frames = 0;
                    check(capture->GetBuffer(&audio, &frames, &flags, nullptr, nullptr));
                    const uint32_t packet[2] = {frames, flags};
                    DWORD length = frames * format.nBlockAlign;
                    if (flags & AUDCLNT_BUFFERFLAGS_SILENT) {
                        silence.assign(length, 0); audio = silence.data();
                    }
                    connected = write_all(packet, sizeof(packet)) && write_all(audio, length);
                    check(capture->ReleaseBuffer(frames));
                    check(capture->GetNextPacketSize(&count));
                }
            }
            client->Stop();
        } catch (...) {
            client->Stop();
            CancelSynchronousIo(input.native_handle());
            input.join();
            throw;
        }
        CancelSynchronousIo(input.native_handle());
        input.join();
    } catch (const std::exception& exception) {
        fprintf(stderr, "%s\n", exception.what()); exit_code = 5;
    }
    CloseHandle(stop); CloseHandle(samples); CloseHandle(target); CoUninitialize();
    return exit_code;
}
