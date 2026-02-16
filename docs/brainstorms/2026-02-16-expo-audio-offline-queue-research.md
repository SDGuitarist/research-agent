# Expo Audio Recording + Offline Queue: Best Practices Research

**Date:** 2026-02-16
**Category:** Mobile Architecture Research
**Use Case:** Voice memo recorder (3-15 min) with offline queue upload, targeting Whisper transcription

---

## Table of Contents

- [A. Expo Audio Recording](#a-expo-audio-recording)
- [B. Offline Recording Queue](#b-offline-recording-queue)
- [C. Audio Upload to FastAPI / Supabase Storage](#c-audio-upload-to-fastapi--supabase-storage)
- [D. Edge Cases and What Can Go Wrong](#d-edge-cases-and-what-can-go-wrong)
- [E. Expo + Supabase Integration](#e-expo--supabase-integration)
- [F. Recommended Architecture Summary](#f-recommended-architecture-summary)

---

## A. Expo Audio Recording

### A1. Library Choice: expo-audio (NOT expo-av)

**CRITICAL DEPRECATION NOTICE:** `expo-av` is deprecated as of SDK 53 and will not publish new versions for SDK 54+. It was fully removed in SDK 55.

**Use `expo-audio`** (the replacement). It shipped as beta in SDK 52, became stable in SDK 53.

| Library | Status | Notes |
|---------|--------|-------|
| `expo-audio` | **Active, recommended** | Modern hooks-based API, cross-platform |
| `expo-av` | **Deprecated** | No new versions after SDK 53, removed SDK 55 |
| `expo-audio-stream` | Active, third-party | For real-time audio streaming/processing, not needed for simple recording |
| `react-native-audio-api` | Active, third-party | Lower-level Web Audio API implementation, overkill for recording |

**Source:** [Expo SDK 53 Changelog](https://expo.dev/changelog/sdk-53), [expo-av deprecation issue](https://github.com/expo/expo/issues/37259)

### A2. Default Recording Formats (expo-audio)

The `RecordingPresets.HIGH_QUALITY` preset records:

```javascript
// HIGH_QUALITY preset (from official docs)
RecordingPresets.HIGH_QUALITY = {
  isMeteringEnabled: true,
  android: {
    extension: '.m4a',
    outputFormat: AndroidOutputFormat.MPEG_4,
    audioEncoder: AndroidAudioEncoder.AAC,
    sampleRate: 44100,
    numberOfChannels: 2,
    bitRate: 128000,
  },
  ios: {
    extension: '.m4a',
    outputFormat: IOSOutputFormat.MPEG4AAC,
    audioQuality: IOSAudioQuality.MAX,
    sampleRate: 44100,
    numberOfChannels: 2,
    bitRate: 128000,
    linearPCMBitDepth: 16,
    linearPCMIsBigEndian: false,
    linearPCMIsFloat: false,
  },
  web: {
    mimeType: 'audio/webm',
    bitsPerSecond: 128000,
  },
};
```

**Both iOS and Android default to `.m4a` (AAC) at 128kbps stereo.**

**Source:** [Expo Audio Documentation](https://docs.expo.dev/versions/latest/sdk/audio/)

### A3. Format for Whisper Compatibility

**Whisper API accepts:** mp3, mp4, mpeg, mpga, m4a, wav, webm

**Recommended approach: Record as M4A, upload as M4A.**

Why M4A is the best choice for this use case:

| Format | Size per minute (approx) | Whisper compatible | Notes |
|--------|--------------------------|-------------------|-------|
| M4A (128kbps AAC) | ~1 MB/min | Yes | Default Expo format, good quality, small size |
| WAV (16-bit, 44.1kHz) | ~10 MB/min | Yes | 10x larger, no quality benefit for speech |
| MP3 (128kbps) | ~1 MB/min | Yes | Requires format conversion on device |
| WebM | ~1 MB/min | Yes | Web only, not native mobile format |

**File sizes for voice recordings (M4A 128kbps):**

| Duration | Approximate size |
|----------|-----------------|
| 5 min | ~5 MB |
| 10 min | ~10 MB |
| 15 min | ~15 MB |

**Key constraint:** Whisper API has a **25 MB file size limit**. At 128kbps M4A, a 15-minute recording is approximately 15 MB, well within the limit.

**DO NOT convert on the phone.** M4A works directly with Whisper. Format conversion adds complexity, battery drain, and processing time. If you self-host Whisper, M4A still works; ffmpeg on your server can convert if needed.

**Known gotcha:** Some iOS M4A recordings have triggered "invalid format" errors with the OpenAI Whisper API. The root cause is typically the MIME type header, not the actual format. Set `Content-Type: audio/mp4` or `audio/m4a` explicitly when uploading.

**Source:** [OpenAI Speech to Text docs](https://platform.openai.com/docs/guides/speech-to-text), [Whisper format discussion](https://github.com/openai/whisper/discussions/1408)

### A4. Custom Recording Preset for Speech/Whisper

For voice memos specifically, stereo is unnecessary and increases file size. Use a custom mono preset:

```javascript
const VOICE_MEMO_PRESET = {
  isMeteringEnabled: true,  // needed for waveform visualization
  android: {
    extension: '.m4a',
    outputFormat: AndroidOutputFormat.MPEG_4,
    audioEncoder: AndroidAudioEncoder.AAC,
    sampleRate: 16000,       // Whisper's native sample rate
    numberOfChannels: 1,      // Mono — voice doesn't need stereo
    bitRate: 64000,           // 64kbps is plenty for speech
  },
  ios: {
    extension: '.m4a',
    outputFormat: IOSOutputFormat.MPEG4AAC,
    audioQuality: IOSAudioQuality.HIGH,
    sampleRate: 16000,        // Whisper's native sample rate
    numberOfChannels: 1,
    bitRate: 64000,
    linearPCMBitDepth: 16,
    linearPCMIsBigEndian: false,
    linearPCMIsFloat: false,
  },
  web: {
    mimeType: 'audio/webm',
    bitsPerSecond: 64000,
  },
};
```

**Why 16kHz mono at 64kbps:**
- Whisper internally resamples everything to 16kHz mono anyway
- Cuts file size in half compared to HIGH_QUALITY (~0.5 MB/min)
- A 15-minute recording is only ~7.5 MB
- Speech quality is indistinguishable at these settings

### A5. Background Recording (User Locks Phone or Switches Apps)

This is the **hardest problem** in Expo audio recording. Behavior differs significantly between platforms.

**iOS:**
- Works if you configure `UIBackgroundModes` with the `audio` key in your `Info.plist`
- In `app.json` / `app.config.js`:
  ```json
  {
    "expo": {
      "ios": {
        "infoPlist": {
          "UIBackgroundModes": ["audio"]
        }
      }
    }
  }
  ```
- Also requires calling `setAudioModeAsync({ allowsRecording: true })` before recording starts
- Known issue: iOS may silently terminate background recordings after variable durations, especially under memory pressure. No crash log is generated.

**Android:**
- **This is a known pain point.** By default, when the app goes to the background, the recorder pauses and only resumes when the app returns to the foreground.
- **Solution:** Use a foreground service via `@notifee/react-native` or a custom native module to keep the app alive. This shows a persistent notification to the user.
- The Expo config plugin approach:
  ```json
  {
    "expo": {
      "android": {
        "permissions": ["RECORD_AUDIO", "FOREGROUND_SERVICE"]
      }
    }
  }
  ```
- **This requires a development build** (not Expo Go)

**Source:** [GitHub issue #40945](https://github.com/expo/expo/issues/40945), [Background recording Medium article](https://drebakare.medium.com/enabling-background-recording-on-android-with-expo-the-missing-piece-41a24b108f6d)

### A6. Maximum Recording Length

- **No hard API limit** in `expo-audio` documentation
- The deprecated `expo-av` had a documented iOS hard cap at **25 minutes 21 seconds**. It is unclear if this persists in `expo-audio` — test this early.
- Practical limits are storage space and battery life
- **Recommendation:** Test 30-minute recordings on both platforms early in development. Set a soft cap in your UI (e.g., 20 minutes) and warn the user as they approach it.

**Source:** [GitHub discussion #13788](https://github.com/expo/expo/discussions/13788)

### A7. Recording State/Progress UI

**Duration timer:** Use `useAudioRecorderState(recorder)` which provides `isRecording` and `durationMillis`:

```javascript
import { useAudioRecorder, useAudioRecorderState, RecordingPresets } from 'expo-audio';

function RecordingScreen() {
  const recorder = useAudioRecorder(VOICE_MEMO_PRESET);
  const state = useAudioRecorderState(recorder);

  // state.isRecording — boolean
  // state.durationMillis — current recording duration in ms

  const formatDuration = (ms) => {
    const seconds = Math.floor(ms / 1000);
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <View>
      <Text>{formatDuration(state.durationMillis)}</Text>
      {/* ... record/stop buttons */}
    </View>
  );
}
```

**Waveform visualization:** Enable `isMeteringEnabled: true` in the recording preset (already in our custom preset). The recording status callback provides a `metering` value (dB level). Collect these values in an array and render them as a simple bar chart or waveform.

Libraries for waveform rendering:
- `@simform_solutions/react-native-audio-waveform` — native waveform visualization
- `@lodev09/expo-recorder` — wrapper around expo-audio with built-in animated waveform
- Custom implementation using React Native's `View` components with animated heights

**Source:** [Expo Audio docs](https://docs.expo.dev/versions/latest/sdk/audio/), [BNA UI Audio Recorder](https://ui.ahmedbna.com/docs/components/audio-recorder)

### A8. Permissions

**Microphone permission is required.** Use `expo-audio`'s built-in permission API:

```javascript
import { AudioModule } from 'expo-audio';

// Check without prompting
const { granted } = await AudioModule.getRecordingPermissionsAsync();

// Request permission (shows OS dialog)
const { status, granted } = await AudioModule.requestRecordingPermissionsAsync();
```

**iOS config plugin** (custom permission message in `app.json`):

```json
{
  "expo": {
    "plugins": [
      [
        "expo-audio",
        {
          "microphonePermission": "This app needs microphone access to record voice memos."
        }
      ]
    ]
  }
}
```

**Android:** `RECORD_AUDIO` permission is added automatically by the expo-audio config plugin.

**Handling denial gracefully:**
- First denial: Explain why the app needs the mic, then re-request
- Second denial (permanent): Direct user to Settings with `Linking.openSettings()`
- Never block the entire app — show a clear message and disable only the recording feature

### A9. Handling Interruptions (Phone Call During Recording)

expo-audio provides interruption events. The `RecordingInterruptionEvent` includes reasons:
- `audioFocusLoss` / `audioFocusGain`
- `phoneCall` / `phoneCallEnded`

```javascript
// Audio mode setup
await setAudioModeAsync({
  playsInSilentMode: true,
  allowsRecording: true,
  interruptionMode: 'doNotMix',  // pause other audio
});
```

**Known issue:** When a phone call interrupts recording, the recording stops but may not automatically resume after the call ends, unlike the built-in iOS Voice Memos app. You need to handle this manually:

- Listen for interruption events
- Save the current recording when interrupted
- Start a new recording when the interruption ends
- Optionally concatenate files server-side

**Recommendation:** Treat phone call interruption as a "save point." Save the partial recording, and when the user returns, offer to continue as a new segment. This is more reliable than trying to resume mid-file.

**Source:** [GitHub issue #31964](https://github.com/expo/expo/issues/31964), [Expo forum thread](https://forums.expo.dev/t/audio-recording-interruption-in-ios/24405)

---

## B. Offline Recording Queue

### B1. Queue Architecture Pattern

```
Record -> Save to documentDirectory -> Add to queue (MMKV) -> Upload when online
```

**Core components:**
1. **Recording storage:** `expo-file-system` `documentDirectory` (persists across app restarts, not cleared by OS)
2. **Queue state:** `react-native-mmkv` (synchronous, 30x faster than AsyncStorage, encrypted)
3. **Connectivity detection:** `@react-native-community/netinfo`
4. **Background upload:** `expo-background-task` (SDK 53+)

### B2. Connectivity Detection

```javascript
import NetInfo from '@react-native-community/netinfo';

// One-time check
const state = await NetInfo.fetch();
console.log(state.isConnected);    // true/false
console.log(state.type);           // 'wifi', 'cellular', etc.
console.log(state.isInternetReachable); // true/false (actual internet, not just connected)

// Subscribe to changes
const unsubscribe = NetInfo.addEventListener(state => {
  if (state.isConnected && state.isInternetReachable) {
    processUploadQueue();
  }
});

// Cleanup
unsubscribe();
```

**Important:** `isConnected` means connected to a network. `isInternetReachable` means actual internet access. Always check `isInternetReachable` before attempting uploads — a user can be connected to WiFi with no internet.

**Source:** [Expo NetInfo docs](https://docs.expo.dev/versions/latest/sdk/netinfo/)

### B3. Persisting the Upload Queue (MMKV)

**Use `react-native-mmkv` over AsyncStorage.**

| Feature | MMKV | AsyncStorage |
|---------|------|--------------|
| Speed | 30x faster | Baseline |
| API | Synchronous | Async/await |
| Encryption | Built-in | None |
| Max value size | No limit | 2MB on Android |

```javascript
import { MMKV } from 'react-native-mmkv';

const storage = new MMKV({ id: 'upload-queue' });

// Queue item shape
interface QueueItem {
  id: string;              // UUID
  filePath: string;        // path in documentDirectory
  fileName: string;        // original filename
  durationMs: number;      // recording duration
  createdAt: string;       // ISO timestamp
  status: 'pending' | 'uploading' | 'failed' | 'complete';
  retryCount: number;
  lastAttempt: string | null;
  fileSize: number;        // bytes
  error: string | null;
}

// Save queue
function saveQueue(items: QueueItem[]) {
  storage.set('queue', JSON.stringify(items));
}

// Load queue (synchronous!)
function loadQueue(): QueueItem[] {
  const raw = storage.getString('queue');
  return raw ? JSON.parse(raw) : [];
}

// Add item to queue
function enqueue(item: QueueItem) {
  const queue = loadQueue();
  queue.push(item);
  saveQueue(queue);
}

// Update item status
function updateStatus(id: string, status: QueueItem['status'], error?: string) {
  const queue = loadQueue();
  const idx = queue.findIndex(q => q.id === id);
  if (idx !== -1) {
    queue[idx].status = status;
    queue[idx].lastAttempt = new Date().toISOString();
    if (error) queue[idx].error = error;
    if (status === 'failed') queue[idx].retryCount += 1;
    saveQueue(queue);
  }
}
```

**MMKV requires a development build** (native module). It does not work in Expo Go.

**Source:** [react-native-mmkv GitHub](https://github.com/mrousavy/react-native-mmkv)

### B4. What Happens if the App is Killed During Upload

- **The upload is lost.** There is no automatic resume for a standard HTTP upload.
- **Mitigation strategy:**
  1. Mark the item as `uploading` before starting
  2. On app restart, check the queue: any item still marked `uploading` should be reset to `pending`
  3. Re-attempt the upload from the beginning
  4. For large files (10+ minutes), use TUS resumable uploads (see Section C)

```javascript
// On app startup — recovery
function recoverQueue() {
  const queue = loadQueue();
  let changed = false;
  for (const item of queue) {
    if (item.status === 'uploading') {
      item.status = 'pending';  // Reset stale uploads
      item.error = 'App was closed during upload';
      changed = true;
    }
  }
  if (changed) saveQueue(queue);
}
```

### B5. Retry Strategy: Exponential Backoff with Jitter

```javascript
const MAX_RETRIES = 5;
const BASE_DELAY_MS = 1000;   // 1 second
const MAX_DELAY_MS = 60000;   // 1 minute

function getRetryDelay(retryCount: number): number {
  const exponentialDelay = BASE_DELAY_MS * Math.pow(2, retryCount);
  const cappedDelay = Math.min(exponentialDelay, MAX_DELAY_MS);
  // Add jitter (0-50% of delay) to prevent thundering herd
  const jitter = Math.random() * cappedDelay * 0.5;
  return cappedDelay + jitter;
}

// Retry schedule (approximate):
// Attempt 1: immediate
// Attempt 2: ~1-1.5s
// Attempt 3: ~2-3s
// Attempt 4: ~4-6s
// Attempt 5: ~8-12s
// After 5 failures: mark as 'failed', require manual retry
```

**When to NOT retry:**
- 401/403 (auth issue, not transient)
- 413 (file too large, won't succeed on retry)
- 422 (validation error)

**When to retry:**
- Network timeout
- 500/502/503 (server error, likely transient)
- Connection refused

### B6. Upload Status UI

Show a queue status screen with per-item states:

```
| Status     | Icon    | Color   | User action       |
|------------|---------|---------|-------------------|
| pending    | clock   | gray    | "Waiting..."      |
| uploading  | spinner | blue    | "Uploading... 45%"|
| failed     | x-mark  | red     | "Retry" button    |
| complete   | check   | green   | "Done"            |
```

Show a persistent badge or banner when items are queued:
- "3 recordings waiting to upload"
- "Uploading 1 of 3..."
- "All recordings uploaded"

### B7. Background Upload

**`expo-background-task` (SDK 53+)** replaces the older `expo-background-fetch`. It uses system-managed scheduling:

```javascript
import * as BackgroundTask from 'expo-background-task';
import * as TaskManager from 'expo-task-manager';

const UPLOAD_TASK = 'UPLOAD_RECORDINGS';

TaskManager.defineTask(UPLOAD_TASK, async () => {
  const queue = loadQueue();
  const pending = queue.filter(q => q.status === 'pending');

  if (pending.length === 0) {
    return BackgroundTask.BackgroundTaskResult.NoData;
  }

  try {
    // Upload the first pending item
    await uploadRecording(pending[0]);
    return BackgroundTask.BackgroundTaskResult.NewData;
  } catch (error) {
    return BackgroundTask.BackgroundTaskResult.Failed;
  }
});

// Register on app startup
await BackgroundTask.registerTaskAsync(UPLOAD_TASK, {
  minimumInterval: 15 * 60, // iOS minimum is 15 minutes
});
```

**Caveats:**
- iOS: Background tasks run at the OS's discretion; you cannot guarantee when they execute
- iOS: Minimum interval is 15 minutes; the OS may delay further based on battery/usage patterns
- Android: More reliable with foreground services, but still not instant
- **Recommendation:** Use background tasks as a safety net, but trigger uploads immediately when the app is in the foreground and connected. Don't rely on background tasks as the primary upload mechanism.

**Source:** [Expo Background Task docs](https://docs.expo.dev/versions/latest/sdk/background-task/), [Expo blog on background tasks](https://expo.dev/blog/goodbye-background-fetch-hello-expo-background-task)

### B8. File Storage on Device

**Use `FileSystem.documentDirectory`** (NOT `cacheDirectory`):

```javascript
import * as FileSystem from 'expo-file-system';

// documentDirectory: persistent, NOT cleared by OS
// cacheDirectory: can be cleared by OS when storage is low

const RECORDINGS_DIR = `${FileSystem.documentDirectory}recordings/`;

// Create directory on app startup
await FileSystem.makeDirectoryAsync(RECORDINGS_DIR, { intermediates: true });

// After recording stops, move from temp to recordings dir
const tempUri = recorder.uri;  // expo-audio provides this
const fileName = `memo_${Date.now()}.m4a`;
const destUri = `${RECORDINGS_DIR}${fileName}`;
await FileSystem.moveAsync({ from: tempUri, to: destUri });
```

**Important:** `cacheDirectory` files can be deleted by the OS at any time when the device runs low on storage. Never store recordings there. `documentDirectory` is the safe choice.

**Source:** [Expo FileSystem docs](https://docs.expo.dev/versions/latest/sdk/filesystem/)

---

## C. Audio Upload to FastAPI / Supabase Storage

### C1. Two Upload Strategies

| Strategy | When to use | Pros | Cons |
|----------|-------------|------|------|
| **Direct to Supabase Storage** | Files go to Supabase, server processes later | Simple, no FastAPI file handling | Requires Supabase bucket config, 2-step flow |
| **Multipart to FastAPI** | Server needs the file immediately | Single request, server controls flow | FastAPI handles large files, timeout risk |

**Recommended: Upload to Supabase Storage, then notify FastAPI.**

This decouples file transfer from processing. The mobile app uploads directly to Supabase Storage (using a signed URL), then sends a lightweight POST to FastAPI with the file reference. FastAPI downloads from Supabase Storage for Whisper processing.

### C2. Supabase Storage: Signed URL Upload Pattern

```javascript
import { supabase } from './supabaseClient';

async function uploadRecording(queueItem: QueueItem) {
  const { filePath, fileName } = queueItem;

  // Read file as blob
  const response = await fetch(filePath);
  const blob = await response.blob();

  // Upload to Supabase Storage
  const { data, error } = await supabase.storage
    .from('recordings')
    .upload(`user-id/${fileName}`, blob, {
      contentType: 'audio/mp4',   // M4A content type
      upsert: false,
    });

  if (error) throw error;
  return data.path;
}
```

### C3. TUS Resumable Upload (for files > 6 MB)

Supabase Storage supports the TUS protocol for resumable uploads. **This is the recommended approach for 10-15 minute recordings** which may be 7-15 MB.

```javascript
import * as tus from 'tus-js-client';

async function resumableUpload(filePath: string, fileName: string) {
  const response = await fetch(filePath);
  const blob = await response.blob();

  return new Promise((resolve, reject) => {
    const upload = new tus.Upload(blob, {
      endpoint: `${SUPABASE_URL}/storage/v1/upload/resumable`,
      retryDelays: [0, 1000, 3000, 5000],
      headers: {
        authorization: `Bearer ${SUPABASE_ANON_KEY}`,
        'x-upsert': 'false',
      },
      metadata: {
        bucketName: 'recordings',
        objectName: `user-id/${fileName}`,
        contentType: 'audio/mp4',
      },
      chunkSize: 6 * 1024 * 1024, // 6MB chunks (Supabase default)
      onError: reject,
      onProgress: (bytesUploaded, bytesTotal) => {
        const percentage = ((bytesUploaded / bytesTotal) * 100).toFixed(1);
        // Update UI progress
      },
      onSuccess: () => resolve(upload.url),
    });

    upload.start();
  });
}
```

**Why TUS matters:**
- If upload fails at 80%, it resumes from 80%, not 0%
- Critical for cellular connections where drops are frequent
- Supabase TUS URLs are valid for 24 hours
- Built-in retry with `retryDelays`

**Source:** [Supabase Resumable Uploads docs](https://supabase.com/docs/guides/storage/uploads/resumable-uploads), [react-native-resumable-upload-supabase](https://github.com/saimon24/react-native-resumable-upload-supabase)

### C4. Upload Progress Indication

```javascript
// Track progress per queue item
function updateProgress(id: string, bytesUploaded: number, bytesTotal: number) {
  const percentage = Math.round((bytesUploaded / bytesTotal) * 100);
  // Store in state (not MMKV — too frequent)
  setUploadProgress(prev => ({ ...prev, [id]: percentage }));
}
```

### C5. Timeout Handling

For a 15-minute recording (~15 MB at 128kbps, ~7.5 MB at 64kbps) on slow cellular:

| Connection speed | 7.5 MB upload time | 15 MB upload time |
|-----------------|-------------------|-------------------|
| 3G (1 Mbps) | ~60 seconds | ~120 seconds |
| Slow 4G (5 Mbps) | ~12 seconds | ~24 seconds |
| Good 4G (20 Mbps) | ~3 seconds | ~6 seconds |
| WiFi (50 Mbps) | ~1.2 seconds | ~2.4 seconds |

**Recommendations:**
- Set HTTP timeout to 120 seconds for standard upload
- Use TUS resumable upload for anything over 6 MB (handles timeouts automatically)
- On cellular: consider showing "WiFi recommended" for large files but don't block the upload
- Never silently fail — always surface upload state to the user

---

## D. Edge Cases and What Can Go Wrong

### D1. App Crash During Recording

**The recording is likely lost or corrupted.** M4A files require proper finalization (writing the file header/footer with metadata). If the app crashes before `recorder.stop()` is called:
- The temp file on disk may exist but be unplayable because it lacks the finalization data
- Some formats (like WAV) are more recoverable from crashes because the raw PCM data is still there, but M4A (AAC) requires container metadata

**Mitigation:**
- Save recording metadata to MMKV (id, startTime, tempPath) when recording starts
- On next app launch, check for "orphaned" recording metadata
- Attempt to recover: try to read the temp file; if it plays, move it to the queue
- If it doesn't play, discard it and inform the user that a recording was lost
- Consider periodic "save points" — stop and restart recording every 5 minutes, concatenate server-side

### D2. Storage Space Running Low

```javascript
import * as FileSystem from 'expo-file-system';

async function checkStorage() {
  const free = await FileSystem.getFreeDiskStorageAsync();
  const freeMB = free / (1024 * 1024);

  if (freeMB < 50) {
    // Warn user: "Low storage. Recording may fail."
    // Suggest uploading pending recordings or clearing completed ones
  }
  if (freeMB < 20) {
    // Disable recording, show clear message
  }
}

// Also: clean up completed uploads
async function cleanupCompletedUploads() {
  const queue = loadQueue();
  const completed = queue.filter(q => q.status === 'complete');
  for (const item of completed) {
    await FileSystem.deleteAsync(item.filePath, { idempotent: true });
  }
  saveQueue(queue.filter(q => q.status !== 'complete'));
}
```

### D3. Queue Builds Up in Airplane Mode

If a user records in airplane mode for hours, the queue could grow to multiple gigabytes.

**Protections:**
- Track total queued file size in MMKV
- Warn at 500 MB: "You have 500 MB of recordings waiting to upload. Connect to WiFi to upload."
- Hard limit at 1 GB or device storage threshold: "Storage full. Please connect to WiFi to upload pending recordings before recording more."
- Prioritize uploading in FIFO order (oldest first)
- On WiFi: upload all pending items in parallel (max 2-3 concurrent)
- On cellular: upload one at a time

### D4. Audio Quality Variations Across Devices

- Cheap Android devices may have noisy microphones — there is nothing you can do about this at the software level
- Some Android devices handle `sampleRate: 16000` differently. If recording fails, fall back to `44100` and let the server downsample for Whisper
- Test on at least 3 Android devices (budget, mid-range, flagship) and 2 iOS devices (older + current)

### D5. iOS vs Android Differences

| Behavior | iOS | Android |
|----------|-----|---------|
| Default format | .m4a (AAC) | .m4a (AAC) |
| Background recording | Works with UIBackgroundModes | Requires foreground service |
| Phone call interruption | Stops recording, needs manual resume | Varies by manufacturer |
| Recording while locked | Works with proper config | Requires foreground service |
| Permission dialog | Shows once, then must go to Settings | Can ask again, then Settings |
| Max recording duration | ~25 min (expo-av, may differ in expo-audio) | No known hard limit |

### D6. Expo Go vs Development Build vs Production

| Feature | Expo Go | Dev Build | Production |
|---------|---------|-----------|------------|
| expo-audio recording | Yes (basic) | Yes (full) | Yes (full) |
| Background recording | No | Yes (with config) | Yes (with config) |
| MMKV storage | No | Yes | Yes |
| Foreground service (Android) | No | Yes | Yes |
| Custom config plugin | No | Yes | Yes |
| expo-background-task | No | Yes | Yes |

**You MUST use a development build for this project.** Expo Go lacks support for:
- Native modules (MMKV)
- Background audio recording configuration
- Foreground services
- Custom config plugins

```bash
# Create a development build
npx expo install expo-dev-client
npx expo prebuild
# Or use EAS Build:
eas build --profile development --platform all
```

### D7. EAS Build Considerations

- **Config plugins** are applied at build time, not runtime. Changes to `app.json` plugins require a new build.
- **iOS entitlements:** Background audio requires the `audio` background mode. This must be declared in your EAS build config.
- **Android foreground service permission:** Declared in `AndroidManifest.xml` via config plugin at build time.
- **Push notifications for upload status:** If you want to notify users when background uploads complete, you'll need `expo-notifications` configured in EAS.
- **Build profiles:** Create `development`, `preview`, and `production` profiles in `eas.json` to test recording and upload behavior at each stage.

---

## E. Expo + Supabase Integration

### E1. Setup

```bash
npx expo install @supabase/supabase-js @react-native-async-storage/async-storage expo-secure-store
```

```javascript
// lib/supabase.ts
import { createClient } from '@supabase/supabase-js';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const ExpoSecureStoreAdapter = {
  getItem: (key: string) => SecureStore.getItemAsync(key),
  setItem: (key: string, value: string) => SecureStore.setItemAsync(key, value),
  removeItem: (key: string) => SecureStore.deleteItemAsync(key),
};

export const supabase = createClient(
  process.env.EXPO_PUBLIC_SUPABASE_URL!,
  process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY!,
  {
    auth: {
      storage: Platform.OS === 'web'
        ? undefined                    // uses localStorage on web
        : ExpoSecureStoreAdapter,      // uses SecureStore on mobile
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,       // important for React Native
    },
  }
);
```

**Source:** [Expo Supabase guide](https://docs.expo.dev/guides/using-supabase/), [Supabase Expo quickstart](https://supabase.com/docs/guides/getting-started/quickstarts/expo-react-native)

### E2. Auth for a Single-User App

For a single-user app, the simplest approach:

**Option A: Email/password auth (simplest)**
- Create one account during onboarding
- Session persists via SecureStore
- RLS policies ensure only that user can access their data
- No social auth complexity

```javascript
// One-time signup
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'securepassword',
});

// Auto-login on app start (session persisted in SecureStore)
const { data: { session } } = await supabase.auth.getSession();
if (!session) {
  // Redirect to login screen
}
```

**Option B: Anonymous auth (even simpler)**
- Supabase supports anonymous sign-in
- No email/password needed
- User gets a UUID and JWT
- Can later "link" to a real identity if needed
- Risk: if user uninstalls, they lose their anonymous identity

```javascript
const { data, error } = await supabase.auth.signInAnonymously();
```

**Option C: API key with no auth (not recommended)**
- Using only the anon key with no auth means anyone with the key can access data
- Even for single-user apps, use at least anonymous auth to get RLS protection

### E3. Real-Time Subscriptions

Useful for showing sync status or processing results:

```javascript
// Subscribe to recording processing status updates
const channel = supabase
  .channel('recording-updates')
  .on(
    'postgres_changes',
    { event: 'UPDATE', schema: 'public', table: 'recordings' },
    (payload) => {
      // Update local state when server finishes processing
      if (payload.new.status === 'transcribed') {
        // Show transcription result
      }
    }
  )
  .subscribe();

// Cleanup
channel.unsubscribe();
```

### E4. Storage Bucket Configuration

Create a `recordings` bucket in Supabase Dashboard with:
- **Public:** No (private bucket)
- **File size limit:** 50 MB (generous for 15-min recordings)
- **Allowed MIME types:** `audio/mp4`, `audio/m4a`, `audio/mpeg`

RLS policy for storage:
```sql
-- Users can only upload to their own folder
CREATE POLICY "Users can upload recordings"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'recordings'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Users can only read their own recordings
CREATE POLICY "Users can read own recordings"
ON storage.objects FOR SELECT
USING (
  bucket_id = 'recordings'
  AND auth.uid()::text = (storage.foldername(name))[1]
);
```

---

## F. Recommended Architecture Summary

### Technology Stack

| Concern | Library | Version note |
|---------|---------|-------------|
| Audio recording | `expo-audio` | SDK 53+ (NOT expo-av) |
| File system | `expo-file-system` | Use documentDirectory |
| Queue persistence | `react-native-mmkv` | Requires dev build |
| Connectivity | `@react-native-community/netinfo` | Expo-compatible |
| Background tasks | `expo-background-task` | SDK 53+ |
| File upload | `tus-js-client` + Supabase Storage | TUS for files > 6MB |
| Backend auth | `@supabase/supabase-js` | With expo-secure-store |
| State management | Zustand or React Context | For upload progress UI |

### Data Flow

```
1. User taps Record
2. Request microphone permission (expo-audio)
3. Set audio mode (allowsRecording: true, playsInSilentMode: true)
4. Start recording with VOICE_MEMO_PRESET (16kHz, mono, 64kbps M4A)
5. Show duration timer + waveform from metering data
6. User taps Stop
7. Move file from temp to documentDirectory/recordings/
8. Add QueueItem to MMKV queue (status: 'pending')
9. If online: start upload immediately
   - File < 6MB: standard Supabase upload
   - File >= 6MB: TUS resumable upload
10. If offline: item stays in queue, NetInfo listener triggers upload when connected
11. On upload success: POST to FastAPI with file reference, mark queue item 'complete'
12. Background task: periodically checks and uploads any pending items
13. Cleanup: delete local files after confirmed upload
```

### Critical "Do" and "Don't" Summary

**DO:**
- Use `expo-audio`, not `expo-av`
- Use a development build from day one (not Expo Go)
- Record in M4A format (works directly with Whisper)
- Use 16kHz mono 64kbps for voice (half the file size, same Whisper quality)
- Store recordings in `documentDirectory` (persistent)
- Use MMKV for queue persistence (synchronous, fast, encrypted)
- Use TUS resumable upload for files > 6MB
- Handle interruptions by saving partial recordings
- Test background recording on real Android devices early
- Set up a foreground service for Android background recording
- Check `isInternetReachable`, not just `isConnected`
- Clean up local files after confirmed upload

**DON'T:**
- Don't use `expo-av` (deprecated, removed in SDK 55)
- Don't use Expo Go for development (lacks native module support)
- Don't store recordings in `cacheDirectory` (OS can delete them)
- Don't convert audio format on device (M4A works with Whisper directly)
- Don't use AsyncStorage for the upload queue (slow, no encryption, async-only)
- Don't rely solely on background tasks for uploads (OS controls timing)
- Don't retry on 401/403/413/422 errors (not transient)
- Don't assume background recording works the same on iOS and Android
- Don't ignore the 25 MB Whisper file size limit (use mono/64kbps to stay well under)
- Don't silently fail uploads — always surface status to the user

---

## Sources

- [Expo Audio (expo-audio) Documentation](https://docs.expo.dev/versions/latest/sdk/audio/)
- [Expo Audio (expo-av) — Deprecated](https://docs.expo.dev/versions/latest/sdk/audio-av/)
- [Expo SDK 53 Changelog](https://expo.dev/changelog/sdk-53)
- [Expo Background Task Documentation](https://docs.expo.dev/versions/latest/sdk/background-task/)
- [Expo FileSystem Documentation](https://docs.expo.dev/versions/latest/sdk/filesystem/)
- [Expo NetInfo Documentation](https://docs.expo.dev/versions/latest/sdk/netinfo/)
- [Expo Go vs Development Builds](https://expo.dev/blog/expo-go-vs-development-builds)
- [Expo Background Task Blog Post](https://expo.dev/blog/goodbye-background-fetch-hello-expo-background-task)
- [Supabase Expo React Native Quickstart](https://supabase.com/docs/guides/getting-started/quickstarts/expo-react-native)
- [Supabase Resumable Uploads](https://supabase.com/docs/guides/storage/uploads/resumable-uploads)
- [Supabase React Native File Upload Blog](https://supabase.com/blog/react-native-storage)
- [OpenAI Speech to Text (Whisper) Documentation](https://platform.openai.com/docs/guides/speech-to-text)
- [Whisper Format Discussion (GitHub)](https://github.com/openai/whisper/discussions/1408)
- [react-native-mmkv GitHub](https://github.com/mrousavy/react-native-mmkv)
- [Android Background Recording Issue (#40945)](https://github.com/expo/expo/issues/40945)
- [expo-av Deprecation Docs Issue (#37259)](https://github.com/expo/expo/issues/37259)
- [Phone Call Interruption Issue (#31964)](https://github.com/expo/expo/issues/31964)
- [iOS Background Recording Termination (#16807)](https://github.com/expo/expo/issues/16807)
- [Recording Corruption Issue (#25842)](https://github.com/expo/expo/issues/25842)
- [Android Background Recording Article (Medium)](https://drebakare.medium.com/enabling-background-recording-on-android-with-expo-the-missing-piece-41a24b108f6d)
- [TUS Resumable Upload for Supabase (GitHub)](https://github.com/saimon24/react-native-resumable-upload-supabase)
- [react-native-audio-waveform (GitHub)](https://github.com/SimformSolutionsPvtLtd/react-native-audio-waveform)
- [BNA UI Audio Recorder Component](https://ui.ahmedbna.com/docs/components/audio-recorder)
