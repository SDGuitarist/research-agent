# Voice-to-Structured-Data Pipeline: Research & Best Practices

**Date:** 2026-02-16
**Type:** Research brainstorm
**Use case:** Solo business owner records post-gig voice memos (3-15 min), uploads from Expo app to FastAPI backend, Whisper transcribes, Claude parses into structured records, user reviews on phone

---

## A. Whisper Transcription

### A1. OpenAI Whisper API vs Self-Hosted

**Recommendation: Use the OpenAI API. Do not self-host.**

The math is straightforward for 8-10 recordings/month at ~5 min average:

| Factor | OpenAI API | Self-Hosted |
|--------|-----------|-------------|
| Cost | ~50 min/month x $0.006/min = **$0.30/month** | GPU instance minimum ~$276/month |
| Setup | Zero — one API call | Docker, GPU drivers, model weights, monitoring |
| Maintenance | None | OS patches, model updates, uptime monitoring |
| Break-even | N/A | ~500+ hours/month of transcription |
| Latency | ~30 seconds for 5 min audio | Depends on hardware |

At $0.30/month, the API is essentially free for this volume. Self-hosting only makes sense above 500 hours/month — roughly 1,000x the projected usage.

**Newer model option:** OpenAI released `gpt-4o-mini-transcribe` in late 2025, which costs **$0.003/min** (half the price of `whisper-1`) and has better word error rates in noisy environments. For a solo developer, this is the best choice.

**Cost estimate at scale:**
- 10 recordings x 5 min avg = 50 min/month
- At $0.003/min (gpt-4o-mini-transcribe): **$0.15/month**
- At $0.006/min (whisper-1): **$0.30/month**
- Even doubling usage to 20 recordings: $0.30-$0.60/month

Sources:
- [Whisper API Pricing Comparison](https://brasstranscripts.com/blog/openai-whisper-api-pricing-2025-self-hosted-vs-managed)
- [OpenAI Community: API vs Self-Hosted](https://community.openai.com/t/is-whisper-api-really-10x-more-expensive-than-self-hosted/576427)
- [OpenAI Next-Gen Audio Models](https://openai.com/index/introducing-our-next-generation-audio-models/)


### A2. How Whisper Handles Car Audio (Road Noise, Phone Mic, Wind)

**It handles it better than expected, but with caveats.**

Whisper was trained on 680,000 hours of diverse audio including noisy environments. However, car audio has specific challenges:

- **Road noise** sits in the same frequency band as many consonants (fricatives like "s", "f", "sh"), so Whisper may confuse these
- **Wind noise** on phone mics causes low-frequency rumble that can mask speech
- **Phone mic quality** varies wildly between devices — modern iPhones have good noise cancellation, older Androids may not

**What to do about it:**

1. **Do NOT pre-process with traditional denoising.** The OpenAI Whisper team and community consensus is clear: traditional denoising (spectral subtraction, noise gates) modifies the spectral representation in ways that hurt Whisper more than help. Whisper's neural network already handles noise internally.

2. **DO use the `prompt` parameter** to prime Whisper with domain-specific vocabulary:
```python
transcription = client.audio.transcriptions.create(
    model="gpt-4o-mini-transcribe",
    file=audio_file,
    language="en",
    prompt="Voice memo about music gigs. May mention venue names, "
           "contact names, phone numbers, song titles, set lists, "
           "sound equipment, and payment amounts."
)
```
The prompt helps Whisper resolve ambiguous sounds toward domain-relevant words.

3. **Consider Facebook Demucs** only if car recordings are consistently terrible. Demucs is a neural source separation tool that isolates voice from background noise. It is heavy (requires its own model download) and adds pipeline complexity, so only reach for it if transcription quality is unacceptable without it.

4. **Voice Activity Detection (VAD)** is lightweight and useful. The `silero-vad` library can strip non-speech segments before sending to Whisper, reducing cost and improving accuracy. Processing 30 seconds of audio takes <1ms on CPU.

Sources:
- [Whisper GitHub Discussion: Preprocessing](https://github.com/openai/whisper/discussions/2125)
- [Whisper GitHub Discussion: Reducing Hallucinations from Noisy Audio](https://github.com/openai/whisper/discussions/2378)
- [OpenAI Cookbook: Whisper Processing Guide](https://cookbook.openai.com/examples/whisper_processing_guide)


### A3. Audio Format: What Should Expo Record In?

**Recommendation: Record in M4A (AAC) at 44100 Hz, mono, 64-128 kbps.**

This is the format that balances file size, Whisper compatibility, and Expo's native support.

**Expo recording configuration:**
```javascript
// Custom preset optimized for voice + Whisper
const VOICE_MEMO_PRESET = {
  isMeteringEnabled: true,
  android: {
    extension: '.m4a',
    outputFormat: AndroidOutputFormat.MPEG_4,
    audioEncoder: AndroidAudioEncoder.AAC,
    sampleRate: 44100,
    numberOfChannels: 1,  // Mono — voice doesn't need stereo
    bitRate: 64000,        // 64 kbps is plenty for speech
  },
  ios: {
    extension: '.m4a',
    outputFormat: IOSOutputFormat.MPEG4AAC,
    audioQuality: IOSAudioQuality.HIGH,  // HIGH, not MAX
    sampleRate: 44100,
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

**Why these choices:**
- **M4A/AAC** is natively supported on both iOS and Android without additional codecs. Whisper accepts m4a, mp3, mp4, mpeg, mpga, wav, and webm.
- **Mono (1 channel)** cuts file size in half versus stereo with no loss for single-speaker voice.
- **64 kbps** is sufficient for speech intelligibility. A 15-min recording at 64 kbps mono = ~7 MB, well under Whisper's 25 MB limit.
- **44100 Hz sample rate** is standard and supported everywhere. You could go down to 16000 Hz for pure speech, but 44100 Hz gives Whisper more information to work with in noisy environments.

**Do NOT use WAV** unless you have a specific reason. WAV files at 15 minutes would be ~150 MB uncompressed, far exceeding the 25 MB API limit and consuming mobile data.

Sources:
- [Expo Audio Recording Documentation](https://docs.expo.dev/versions/latest/sdk/audio-av/)
- [Expo GitHub Discussion: WAV Recording](https://github.com/expo/expo/discussions/24034)
- [Making Speech-to-Text Work with Expo](https://fostermade.co/about/journal/making-speech-to-text-work-with-react-native-and-expo)


### A4. Audio Preprocessing: Do We Need Noise Reduction?

**No. Skip traditional noise reduction. Use the prompt parameter instead.**

Community consensus from the Whisper GitHub discussions and the OpenAI Cookbook:

1. **De-noising modifies the spectral representation** of audio, which can distort frequency bands and hurt ASR performance
2. **Whisper's internal noise handling** is already trained on noisy data
3. **The prompt parameter** is the highest-ROI preprocessing — it biases the model toward your domain vocabulary

**The exception:** If a recording is so noisy that a human cannot understand it, Whisper will not magically fix it. In that case, consider:
- **Demucs** (neural voice separation) as a last resort
- Telling the user to re-record in a quieter environment
- Flagging the recording as low-confidence in the UI

**Lightweight preprocessing that IS worth doing:**
- **Normalize audio levels** (prevent clipping or very quiet recordings)
- **Trim leading/trailing silence** (reduces cost, faster processing)
- **VAD gating** with silero-vad (strip long non-speech segments)

```python
from pydub import AudioSegment
from pydub.effects import normalize

# Normalize audio levels
audio = AudioSegment.from_file("memo.m4a")
audio = normalize(audio)
audio.export("memo_normalized.m4a", format="mp4")
```


### A5. Max Audio Length and Chunking

**Whisper API limit: 25 MB file size. No explicit duration limit.**

At the recommended settings (M4A, 64 kbps, mono):
- 5 min recording = ~2.4 MB
- 10 min recording = ~4.8 MB
- 15 min recording = ~7.2 MB
- **You will NOT hit the 25 MB limit** with these settings

**When you do need chunking** (future-proofing for longer recordings):

```python
from pydub import AudioSegment
from pydub.silence import split_on_silence

def chunk_audio(file_path, max_size_mb=24):
    """Split audio on silence boundaries if file exceeds max_size_mb."""
    audio = AudioSegment.from_file(file_path)
    file_size_mb = len(audio.raw_data) / (1024 * 1024)

    if file_size_mb <= max_size_mb:
        return [file_path]  # No chunking needed

    chunks = split_on_silence(
        audio,
        min_silence_len=700,    # 700ms pause = natural sentence break
        silence_thresh=-40,      # dB threshold for silence
        keep_silence=300,        # Keep 300ms of silence at boundaries
    )

    # Merge small chunks to avoid tiny segments
    merged = []
    current = AudioSegment.empty()
    for chunk in chunks:
        if len(current) + len(chunk) < 10 * 60 * 1000:  # 10 min max
            current += chunk
        else:
            merged.append(current)
            current = chunk
    if len(current) > 0:
        merged.append(current)

    return merged
```

**Critical: Maintain context across chunks.** Use the `prompt` parameter to feed the last ~200 words of the previous chunk's transcript into the next chunk's transcription call. This prevents Whisper from losing context at boundaries.

```python
previous_transcript = ""
full_transcript = ""

for chunk in audio_chunks:
    transcription = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=chunk,
        language="en",
        prompt=previous_transcript[-800:]  # ~200 words, Whisper uses last 224 tokens
    )
    full_transcript += transcription.text + " "
    previous_transcript = transcription.text
```

Sources:
- [OpenAI Community: File Size Limits](https://community.openai.com/t/whisper-api-increase-file-limit-25-mb/566754)
- [OpenAI Audio API FAQ](https://help.openai.com/en/articles/7031512-audio-api-faq)
- [Building Long Audio Transcription with Whisper](https://www.buildwithmatija.com/blog/building-a-long-audio-transcription-tool-with-openai-s-whisper-api)


### A6. Word-Level Timestamps

**Available but not critical for the initial version. Add later if needed.**

Whisper supports word-level timestamps via the `verbose_json` response format:

```python
transcription = client.audio.transcriptions.create(
    model="whisper-1",  # Note: check if gpt-4o-mini-transcribe supports this
    file=audio_file,
    response_format="verbose_json",
    timestamp_granularities=["word", "segment"]
)
# Returns segments with start/end times and individual word timestamps
```

**Use cases for your pipeline:**
- Let the user tap a parsed entity (e.g., "Sarah Miller") and jump to that point in the audio to verify
- Highlight the source audio passage for low-confidence extractions
- Allow the user to replay just the 10 seconds around a phone number to verify digits

**Caveats:**
- Word-level timestamps add latency to the API call
- Whisper was not explicitly trained for word-level timing — it uses an inference-time trick, so timestamps are approximate (off by ~0.1-0.5 seconds)
- Segment-level timestamps (sentence-level) are free with no extra latency

**Recommendation:** Start with segment-level timestamps (`timestamp_granularities=["segment"]`). They are accurate enough for "jump to this part of the recording" and have zero additional latency. Add word-level later if users request it.

Sources:
- [OpenAI API: Audio Timestamps](https://platform.openai.com/docs/api-reference/audio/)
- [OpenAI Community: Word-Level Timestamps](https://community.openai.com/t/whisper-api-word-level-time-stamping/123199)


---

## B. AI Parsing of Unstructured Transcripts

### B1. Extracting Structured Entities from Stream-of-Consciousness Text

**This is the hardest part of the pipeline.** Stream-of-consciousness voice memos mix entities unpredictably:

> "So the gig at The Blue Note went great, Sarah the manager said we can come back in March, her number is 555-0142, oh and I need to follow up with the sound guy Dave about the monitor mix, the pay was $800 for the night, I should also remember to bring extra cables next time..."

From this, you need to extract:
- **Venue:** The Blue Note
- **Contact:** Sarah (manager), phone: 555-0142
- **Contact:** Dave (sound guy)
- **Event details:** pay $800
- **Action items:** Follow up with Dave about monitor mix, bring extra cables

**Recommended approach: Single-pass extraction with Claude's structured outputs.**

Claude is strong enough to handle this in one pass. Two-pass (first extract entities, then classify) adds latency and cost without measurably improving accuracy for this use case.

### B2. One-Pass vs Two-Pass Parsing

**Use one pass for the initial version.**

| Approach | When to use |
|----------|-------------|
| **One-pass** | Transcripts under ~3000 words. Single speaker. Well-defined entity types. |
| **Two-pass** | Very long transcripts (30+ min). Multiple speakers. Need to first identify sections then extract from each. |

For 3-15 minute voice memos from a single speaker, one pass is sufficient and halves your Claude API cost. If accuracy is poor on longer memos, you can add a second pass later where pass 1 segments the transcript into topics and pass 2 extracts entities from each segment.

### B3. Prompt Engineering for Entity Extraction

**Use Claude's structured outputs with a Pydantic schema.**

Define your data models:

```python
from pydantic import BaseModel, Field
from typing import Optional

class ExtractedContact(BaseModel):
    name: str = Field(description="Full name if available, first name otherwise")
    role: Optional[str] = Field(None, description="Role or title mentioned (e.g., 'manager', 'sound guy')")
    organization: Optional[str] = Field(None, description="Venue or company they're associated with")
    phone: Optional[str] = Field(None, description="Phone number exactly as spoken, digits only")
    email: Optional[str] = Field(None, description="Email if mentioned")
    confidence: float = Field(description="0.0-1.0 confidence that this contact was correctly extracted")
    source_quote: str = Field(description="The exact transcript excerpt this was extracted from")

class ExtractedVenue(BaseModel):
    name: str
    location: Optional[str] = None
    contact_name: Optional[str] = None
    notes: Optional[str] = None
    confidence: float
    source_quote: str

class ExtractedActionItem(BaseModel):
    description: str
    assignee: Optional[str] = Field(None, description="Who needs to do this")
    deadline: Optional[str] = Field(None, description="When, if mentioned")
    priority: Optional[str] = Field(None, description="high/medium/low based on urgency language")
    confidence: float
    source_quote: str

class ExtractedEvent(BaseModel):
    venue: Optional[str] = None
    date: Optional[str] = None
    pay: Optional[str] = None
    set_details: Optional[str] = None
    notes: Optional[str] = None
    confidence: float
    source_quote: str

class VoiceMemoExtraction(BaseModel):
    contacts: list[ExtractedContact] = []
    venues: list[ExtractedVenue] = []
    action_items: list[ExtractedActionItem] = []
    events: list[ExtractedEvent] = []
    raw_notes: Optional[str] = Field(None, description="Anything important that doesn't fit the above categories")
    overall_summary: str = Field(description="2-3 sentence summary of the memo")
```

**The extraction call:**

```python
import anthropic
import json

client = anthropic.Anthropic()

def extract_from_transcript(transcript: str, existing_contacts: list[dict] = None):
    existing_context = ""
    if existing_contacts:
        existing_context = (
            "\n\n<existing_records>\n"
            "The user has these existing contacts and venues. "
            "Match mentions to these when possible rather than creating duplicates:\n"
            f"{json.dumps(existing_contacts, indent=2)}\n"
            "</existing_records>"
        )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=(
            "You are extracting structured data from a voice memo transcript. "
            "The speaker is a musician/performer recording notes after a gig.\n\n"
            "CRITICAL RULES:\n"
            "1. Only extract information EXPLICITLY stated in the transcript. "
            "Never infer or hallucinate details not present.\n"
            "2. For phone numbers, extract ONLY the digits actually spoken. "
            "If digits are unclear or incomplete, set confidence below 0.5 "
            "and include what you heard.\n"
            "3. For names, extract exactly what was said. "
            "If only a first name is given, use only the first name.\n"
            "4. Set confidence to 0.0-0.3 for guesses, 0.3-0.7 for probable, "
            "0.7-1.0 for clearly stated.\n"
            "5. Include source_quote: the exact transcript words you based "
            "each extraction on.\n"
            "6. If the transcript is garbled or unintelligible in parts, "
            "note this in raw_notes rather than guessing."
            f"{existing_context}"
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"<transcript>\n{transcript}\n</transcript>\n\n"
                    "Extract all contacts, venues, action items, and event details "
                    "from this voice memo. Include confidence scores and source quotes."
                )
            }
        ],
        # Use structured outputs (beta as of late 2025)
        extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"},
        # Pass the Pydantic schema
        # Note: check current Anthropic SDK docs for exact parameter name
    )

    return response
```

**Key prompt engineering patterns:**

1. **Source quotes** — Force the model to cite its evidence. This is the single most effective anti-hallucination technique. If the model cannot provide a source quote, the extraction is likely fabricated.

2. **Confidence scores** — Ask the model to self-assess. Claude is reasonably well-calibrated: items it marks as low-confidence genuinely tend to be uncertain.

3. **XML boundaries** — Wrap the transcript in `<transcript>` tags to clearly separate the user's content from the instructions. This prevents prompt injection from transcript content.

4. **Existing records context** — Pass the user's existing contacts/venues so Claude can match "Sarah from Blue Note" to an existing record instead of creating a duplicate.

Sources:
- [Claude Structured Outputs Documentation](https://docs.claude.com/en/docs/build-with-claude/structured-outputs)
- [Anthropic Cookbook: Extracting Structured JSON](https://github.com/anthropics/anthropic-cookbook/blob/main/tool_use/extracting_structured_json.ipynb)
- [Claude API Structured Output Guide](https://thomas-wiegold.com/blog/claude-api-structured-output/)


### B4. Handling AI Hallucinations and Misheard Information

**This is the #1 risk in the pipeline.** Common failure modes:

| Failure | Example | Mitigation |
|---------|---------|------------|
| **Invented phone digits** | Transcript says "five five five oh one four" → AI outputs "555-0142" (added a "2") | Require source_quote, flag phone numbers as always-review |
| **Name fabrication** | Transcript says "Sarah" → AI invents "Sarah Miller" | Prompt: "Only use names explicitly stated" |
| **Venue name confusion** | "Blue Note" → AI outputs "The Blue Note Jazz Club, NYC" when it's a local bar | Prompt: "Do not add details not in the transcript" |
| **Merged entities** | Two Daves mentioned → AI combines them into one contact | Prompt: "Create separate entries for each mention" |
| **Missed entities** | Quiet part of recording → entity not transcribed by Whisper → not extracted | Harder to mitigate — see section D |

**Concrete mitigations:**

1. **Source quotes are mandatory.** Every extracted entity must include the exact transcript text it came from. If the model cannot quote the source, reject the extraction.

2. **Phone numbers are ALWAYS flagged for review.** Whisper frequently mishears digits. The AI parsing layer can further garble them. Mark every phone number as confidence < 0.7 regardless of what the model self-reports.

3. **Match against existing records.** If "Sarah" is mentioned and the user has a contact named "Sarah Chen" at "The Blue Note," the match is probably correct. But present it as "Did you mean Sarah Chen?" not as a fait accompli.

4. **Post-extraction validation rules:**
```python
def validate_extraction(extraction: VoiceMemoExtraction) -> list[str]:
    warnings = []
    for contact in extraction.contacts:
        if contact.phone and len(contact.phone.replace("-", "")) not in [7, 10, 11]:
            warnings.append(f"Phone number '{contact.phone}' for {contact.name} "
                          f"has unusual length — verify")
        if contact.confidence < 0.5:
            warnings.append(f"Low confidence contact: {contact.name} — verify")
    for item in extraction.action_items:
        if item.confidence < 0.5:
            warnings.append(f"Low confidence action item: {item.description}")
    return warnings
```


### B5. JSON Output Format

**Use Claude's structured outputs (JSON mode) with Pydantic.**

As of late 2025, Anthropic supports structured outputs in public beta. This compiles your JSON schema into a grammar and constrains token generation at inference time, so the model literally cannot produce invalid JSON.

Two options:
1. **JSON Outputs mode** (`output_format` parameter) — best for data extraction tasks
2. **Strict Tool Use mode** (`strict: true` on tool definitions) — best if you're already using tool_use

For entity extraction, JSON Outputs mode is more natural. The response lands in `response.content[0].text` as guaranteed-valid JSON.

**Even with structured outputs, validate in your code.** The schema guarantees valid JSON structure, but it does not guarantee sensible values (e.g., a phone number field could contain "banana" and still be valid JSON string).


### B6. Providing Context About Existing Records

**Pass a lightweight summary of existing records in the system prompt.**

```python
existing_context = [
    {"name": "Sarah Chen", "role": "venue manager", "org": "The Blue Note"},
    {"name": "Dave Rodriguez", "role": "sound engineer", "org": "freelance"},
    {"name": "The Blue Note", "type": "venue", "city": "Austin"},
    {"name": "Mohawk", "type": "venue", "city": "Austin"},
]
```

**Keep it small.** Do not dump your entire contacts database. Send only:
- Contacts interacted with in the last 90 days
- Venues played at in the last 6 months
- Any entities mentioned in previous memos from the same week

This typically means 20-50 records, which fits comfortably in the system prompt and gives Claude enough context to match ambiguous mentions without overwhelming the context window.


### B7. Handling Garbled or Gap-Filled Transcripts

When Whisper cannot understand audio, it tends to:
- **Hallucinate repetitive phrases** ("Thank you. Thank you. Thank you.")
- **Produce empty segments** (silence → no text)
- **Output nonsense words** (garbled audio → plausible-sounding but wrong words)

**Detection strategies:**
```python
def detect_transcript_quality_issues(transcript: str) -> dict:
    issues = {}

    # Detect repetitive hallucination
    words = transcript.split()
    for i in range(len(words) - 5):
        chunk = " ".join(words[i:i+3])
        if transcript.count(chunk) > 3:
            issues["repetitive_hallucination"] = True
            break

    # Detect very short transcript for audio length
    # (suggests Whisper couldn't understand most of it)
    # Compare word count to expected ~150 words/minute
    issues["word_count"] = len(words)

    # Detect common Whisper hallucination patterns
    hallucination_patterns = [
        "thank you for watching",
        "please subscribe",
        "thanks for watching",
        "like and subscribe",
    ]
    for pattern in hallucination_patterns:
        if pattern.lower() in transcript.lower():
            issues["known_hallucination_pattern"] = pattern
            break

    return issues
```

**What to tell the user:** If the transcript is flagged as potentially garbled, show a warning: "Parts of this recording were hard to understand. Review carefully, and consider re-recording unclear sections."


---

## C. Human Review/Correction UX

### C1. Best Practices for Human-in-the-Loop Review

The key success metric is: **correction must be faster than manual entry.** If it takes longer to fix AI output than to type it from scratch, the feature is a net negative.

**Design principles from successful HITL implementations:**

1. **Show, don't tell.** Present extracted data in editable cards, not a wall of JSON. Each card shows the entity, its source quote from the transcript, and a confidence indicator.

2. **Confidence-based routing.** High-confidence items (>0.8) are pre-approved but editable. Low-confidence items (<0.5) are highlighted and require explicit confirmation. Medium items are shown normally.

3. **Binary first, details second.** First ask "Is this correct? Yes/No" for each entity. Only show editing UI after the user taps "No." This makes the 80% of correct extractions a single tap.

4. **Batch operations.** "Accept all high-confidence items" button for power users who trust the AI after a few sessions.

### C2. The "Review Before Save" Pattern

Successful implementations from comparable apps:

**Otter.ai's approach:**
- Shows full transcript with extracted action items, key topics, and summary in separate tabs
- Allows inline editing of the transcript itself
- Action items can be reassigned, edited, or dismissed individually
- Uses templates ("Project Update", "Sales Call") to structure extraction

**Fireflies' approach:**
- Five-part "Super Summaries" that can be individually enabled/disabled
- AI Apps for custom extraction patterns
- Voice directory for speaker matching

**Recommended UX flow for your app:**

```
1. Recording complete → Upload starts (show progress)
2. Transcription complete → Show transcript with "Parsing..." indicator
3. Parsing complete → Show review screen:

   ┌─────────────────────────────────┐
   │ Voice Memo - Feb 16, 2026       │
   │ Duration: 5:32                  │
   │                                 │
   │ SUMMARY                         │
   │ "Great gig at The Blue Note..." │
   │                                 │
   │ CONTACTS (2 found)         [✓ All]│
   │ ┌─ Sarah ─────────── ⚠ ──────┐ │
   │ │ Role: Manager               │ │
   │ │ Org: The Blue Note          │ │
   │ │ Phone: 555-014_ ← VERIFY   │ │
   │ │ "Sarah the manager said..." │ │
   │ └────────────────────────────┘ │
   │ ┌─ Dave ──────────── ✓ ──────┐ │
   │ │ Role: Sound guy             │ │
   │ │ "follow up with the sound   │ │
   │ │  guy Dave about..."         │ │
   │ └────────────────────────────┘ │
   │                                 │
   │ ACTION ITEMS (2)          [✓ All]│
   │ ☐ Follow up with Dave re:     │
   │   monitor mix                  │
   │ ☐ Bring extra cables           │
   │                                 │
   │ EVENTS (1)                      │
   │ ┌─ The Blue Note gig ── ✓ ───┐ │
   │ │ Pay: $800                   │ │
   │ │ Notes: "went great"         │ │
   │ └────────────────────────────┘ │
   │                                 │
   │   [View Full Transcript]        │
   │                                 │
   │   [ Save All ]  [ Discard ]     │
   └─────────────────────────────────┘
```

**Key UX details:**
- **Warning icon (caution)** on low-confidence items — user must tap to confirm or edit
- **Checkmark** on high-confidence items — pre-approved, tap to edit if needed
- **Source quote** shown under each entity — lets user verify without reading full transcript
- **"View Full Transcript"** link — for when the user wants to check something the AI missed
- **Tapping an entity card** opens an edit sheet with pre-filled fields
- **"Accept All"** checkbox per section — for power users

### C3. Confidence Scores

**Yes, absolutely include them. But present them visually, not numerically.**

Users do not care that confidence is 0.73 vs 0.68. They care about:
- Green checkmark = "AI is pretty sure this is right"
- Yellow warning = "AI is not sure, please check"
- Red flag = "AI is guessing, definitely check"

**Thresholds:**
- **> 0.8**: Auto-approved (green checkmark). User can still edit.
- **0.5 - 0.8**: Needs confirmation (yellow). Card is expanded by default.
- **< 0.5**: Flagged (red). Must be explicitly confirmed or dismissed.

**Phone numbers are special:** Always show yellow/red regardless of AI confidence score. Whisper + Claude is a two-step telephone game for digits.

### C4. Making Correction Faster Than Manual Entry

**This is the make-or-break metric.** Specific techniques:

1. **Pre-filled forms.** The AI fills in everything. The user only corrects mistakes. For a well-transcribed memo, this means 0-3 taps to save everything.

2. **Smart keyboards.** When editing a phone number field, show the numeric keyboard. When editing a name, show autocomplete from existing contacts.

3. **Audio playback per entity.** If you have segment timestamps, let the user tap a play button next to "Phone: 555-014_" to hear just that part of the recording. This is faster than re-listening to the whole memo.

4. **Swipe gestures.** Swipe right to approve, swipe left to dismiss, tap to edit. Borrowed from Tinder/email triage UX patterns that are already muscle memory for mobile users.

5. **Learn from corrections.** If the user corrects "The Blue Note" to "Blue Note Austin" three times, remember that mapping. Store user corrections and include them in the prompt context for future extractions.

### C5. Comparable Apps

| App | What it does well | What to learn |
|-----|------------------|---------------|
| **Otter.ai** | Templates for structured extraction, inline transcript editing | The template concept — let users define what they want extracted |
| **Fireflies** | Customizable AI Apps, five-part summaries | Adaptability — let extraction schema evolve |
| **Fathom** | Persistent speaker memory, minimal setup | Remember previous corrections and apply automatically |
| **Notion AI** | Turns meeting notes into action items and databases | The "extract to database record" UX pattern |
| **Expensify SmartScan** | Receipt → structured expense report | Confidence-based review: green/yellow/red |

Sources:
- [Zapier: Human-in-the-Loop Patterns](https://zapier.com/blog/human-in-the-loop/)
- [Parseur: HITL Complete Guide](https://parseur.com/blog/human-in-the-loop-ai)
- [Unstract: HITL for Document Processing](https://unstract.com/blog/human-in-the-loop-hitl-for-ai-document-processing/)
- [Otter vs Fireflies Comparison](https://www.avoma.com/blog/otter-vs-fireflies)


---

## D. What Can Go Wrong

### D1. Common Failure Modes

**Transcription failures:**

| Failure | Frequency | Impact | Mitigation |
|---------|-----------|--------|------------|
| Whisper hallucination on silence | Common with pauses >5s | Inserts "Thank you for watching" or repeated phrases | Detect patterns, strip known hallucinations |
| Phone number digit errors | Very common | Wrong contact info saved | Always flag for manual review |
| Name mishearing | Common | "Dave" → "Date", "Sarah" → "Sara" | Match against existing contacts, fuzzy matching |
| Background music bleeds into transcript | Occasional at gigs | Lyrics transcribed as speech | VAD preprocessing, or note in prompt that music may be present |
| Whisper API timeout | Rare | Upload fails | Retry with exponential backoff |

**Parsing failures:**

| Failure | Frequency | Impact | Mitigation |
|---------|-----------|--------|------------|
| Claude creates entities not in transcript | Occasional | False data saved | Source quotes, validation |
| Claude merges separate mentions | Occasional | Two people combined into one | Prompt: "create separate entries" |
| Claude misses entities entirely | Uncommon for clear speech | Data loss | User can flag "something's missing" |
| Claude JSON malformation | Rare with structured outputs | Parse error | Structured outputs prevent this; fallback: retry |
| Claude rate limit hit | Unlikely at this volume | Processing delayed | Queue + retry |

**Pipeline failures:**

| Failure | Frequency | Impact | Mitigation |
|---------|-----------|--------|------------|
| File upload interrupted (bad connection) | Common on mobile | Partial upload | Resumable uploads, local queue |
| Audio file corrupted | Rare | Transcription fails | Validate file header before sending to Whisper |
| API key expired/invalid | One-time | Everything breaks | Health check on app startup |
| User's phone runs out of storage | Occasional | Recording truncated | Check available storage before recording |


### D2. Edge Cases

**Multiple speakers:** If someone else talks during the memo (bartender, bandmate), Whisper will transcribe their speech too without distinguishing speakers. The newer `gpt-4o-transcribe-diarize` model supports diarization (speaker identification), but it costs more. For the initial version, note in the prompt that the primary speaker is the user, and other voices may appear.

**Background music at the venue:** This is the hardest edge case for a musician's app. If the user records while music is playing, Whisper may transcribe lyrics as speech. Mitigation: VAD preprocessing, and include in the prompt "Ignore any song lyrics or background music."

**Phone calls during recording:** If the user takes a call mid-recording, the phone may pause or mute the recording depending on the OS. On iOS, `expo-av` recording typically stops when a call comes in. Handle this by checking recording status on resume and notifying the user.

**Very short recordings (<30 seconds):** Whisper may produce hallucinations on very short audio. Add a minimum duration check (e.g., 30 seconds) before processing.

**Non-English words:** Venue names, song titles, or names from other languages. Use `language="en"` to tell Whisper the primary language is English, but these may still be garbled. The prompt can help: "Some venue names or song titles may be in Spanish."


### D3. Privacy and Security

**Voice data is biometric data.** It carries unique voiceprints, emotional states, and potentially captures bystanders' conversations. This matters even for a solo developer.

**Concrete security measures:**

1. **TLS in transit.** Both OpenAI and Anthropic APIs use HTTPS/TLS. Your FastAPI backend should also enforce HTTPS. This is non-negotiable.

2. **Do not store audio longer than necessary.** Once transcription is complete and the user has reviewed the extracted data, delete the audio file from your server. Keep only the transcript and structured data.

3. **OpenAI's data retention policy:** As of 2025, OpenAI's API does not use submitted data for training (their API Terms). Audio sent to Whisper is processed and not retained after transcription. Verify this has not changed.

4. **Anthropic's data policy:** Similarly, Anthropic's API does not train on customer data. Transcripts sent for parsing are not retained.

5. **Local processing option (future):** For privacy-sensitive users, consider running Whisper locally on the phone using `whisper.cpp` or `expo-audio-stream` with a local model. This eliminates sending audio to any third party. Not worth the complexity for V1, but worth noting for the future.

6. **Encrypt audio at rest on the server.** If audio is queued for processing, encrypt it with AES-256. Use a proper key management approach (e.g., environment variable for the key, not hardcoded).

```python
# FastAPI: delete audio after processing
import os

async def process_voice_memo(audio_path: str):
    try:
        transcript = await transcribe_audio(audio_path)
        extraction = await extract_entities(transcript)
        return extraction
    finally:
        # Always delete audio after processing
        if os.path.exists(audio_path):
            os.remove(audio_path)
```


### D4. Missing vs Wrong Extractions

**Missing entities (false negatives)** are less dangerous than **wrong entities (false positives).**

- If the AI misses "Dave the sound guy," the user might notice and add him manually. No data is corrupted.
- If the AI invents "Dave Rodriguez, 555-0199, Stage Manager" from a garbled mention, the user might save incorrect data without noticing.

**Design for false positives being visible:**
- Source quotes make it obvious when an extraction is fabricated (the quote won't match)
- Confidence scores flag uncertain items
- The review step catches errors before they enter the database

**Design for false negatives being recoverable:**
- "Add missing item" button in the review screen
- "View full transcript" link to scan for anything the AI missed
- After a few sessions, users learn to spot gaps and add them quickly


### D5. Rate Limiting and API Failures Mid-Pipeline

**The pipeline has three external API calls:**
1. Upload audio to your server
2. Your server calls Whisper API
3. Your server calls Claude API

**Any of these can fail.** Design for graceful degradation:

```python
from enum import Enum

class PipelineStatus(Enum):
    UPLOADED = "uploaded"           # Audio received by server
    TRANSCRIBING = "transcribing"   # Whisper call in progress
    TRANSCRIBED = "transcribed"     # Transcript ready
    PARSING = "parsing"             # Claude call in progress
    PARSED = "parsed"               # Extraction ready for review
    REVIEWED = "reviewed"           # User approved
    FAILED = "failed"               # Something broke

# Store status in database so the app can poll/resume
```

**Key patterns:**
- **Idempotent retries.** If Whisper fails, retry the same audio file. If Claude fails, retry with the same transcript. Neither has side effects.
- **Save intermediate results.** Store the transcript even if Claude parsing fails. The user can still read the raw transcript. Store the audio even if Whisper fails (retry later).
- **Exponential backoff.** For rate limits (HTTP 429), wait 1s, 2s, 4s, 8s before retrying. Cap at 3 retries.
- **User notification.** If processing fails after retries, notify the user: "Your memo is saved but couldn't be fully processed. We'll retry automatically." Do not silently lose their recording.

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import RateLimitError, APITimeoutError

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
)
async def transcribe_with_retry(client, audio_file):
    return client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=audio_file,
        language="en",
        prompt="Voice memo about music gigs, venues, contacts, and action items."
    )
```

**FastAPI file upload pattern:**

```python
from fastapi import FastAPI, UploadFile, BackgroundTasks
from pathlib import Path
import shutil
import uuid

app = FastAPI()

UPLOAD_DIR = Path("/tmp/voice_memos")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.post("/api/memos/upload")
async def upload_memo(file: UploadFile, background_tasks: BackgroundTasks):
    # Save file to disk FIRST (UploadFile closes after endpoint returns)
    memo_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{memo_id}.m4a"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Queue background processing
    background_tasks.add_task(process_pipeline, memo_id, str(file_path))

    return {"memo_id": memo_id, "status": "uploaded"}
```

**Critical FastAPI gotcha:** The `UploadFile` object is closed after the endpoint handler returns. You MUST read the file contents or save to disk within the endpoint handler, then pass the file path (not the UploadFile) to the background task.

Sources:
- [FastAPI: Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [FastAPI Discussion: UploadFile with BackgroundTasks](https://github.com/fastapi/fastapi/discussions/10936)
- [Speech-to-Text Privacy: Enterprise Security](https://deepgram.com/learn/speech-to-text-privacy)
- [Voice AI Security Best Practices](https://smallest.ai/blog/best-secure-voice-ai-apis-enterprise)


---

## Summary: Recommended Architecture

```
PHONE (Expo)                    SERVER (FastAPI)
─────────────                   ────────────────
Record M4A (64kbps, mono)  ──→  Save to disk
                                     │
                                     ▼
                                Whisper API (gpt-4o-mini-transcribe)
                                  - prompt with domain vocab
                                  - segment timestamps
                                     │
                                     ▼
                                Quality check (hallucination detection)
                                     │
                                     ▼
                                Claude API (structured outputs)
                                  - Pydantic schema
                                  - existing records context
                                  - source quotes + confidence
                                     │
                                     ▼
                                Validation (phone length, etc.)
                                     │
                                     ▼
PHONE (Review UI)  ◄────────  Return parsed data + transcript
  - Confidence-colored cards
  - Source quotes visible
  - Audio playback per entity
  - Accept/Edit/Dismiss per item
  - "Save All" to database
```

**Estimated costs at 10 recordings x 5 min/month:**
- Whisper (gpt-4o-mini-transcribe): $0.15/month
- Claude (Sonnet, ~2000 tokens per extraction): ~$0.20/month
- **Total API costs: ~$0.35/month**

**Libraries to use:**
- `openai` Python SDK — Whisper transcription
- `anthropic` Python SDK — Claude entity extraction
- `pydantic` — Schema definition and validation
- `pydub` + `ffmpeg` — Audio preprocessing (normalization, chunking if needed)
- `tenacity` — Retry logic with exponential backoff
- `expo-av` — Audio recording on the phone
- `silero-vad` (optional) — Voice activity detection for preprocessing

**What to build first (MVP):**
1. Expo recording with the custom voice memo preset
2. FastAPI upload endpoint with background processing
3. Whisper transcription (no preprocessing)
4. Claude extraction with Pydantic schema and confidence scores
5. Simple review UI with Accept/Edit/Dismiss per entity
6. Only add preprocessing, timestamps, and audio playback if quality issues emerge
