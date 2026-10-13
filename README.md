# Fairy

Execute setup.py to install llama and LLM models

## Voice transcription

Install the bot dependencies with `python -m pip install -r requirements.txt`.
The voice receiver uses a pinned DAVE-compatible fork of `discord-ext-voice-recv`
and `discord.py` 2.7. Do not install the original receiver alongside the fork.

Start the local Whisper server with the multilingual model (the default port
8081 avoids conflicting with llama-server on port 8080):

```powershell
python llama_start.py
```

Leave both services running, then start the bot in a second terminal:

```powershell
python bot.py
```

Run `/join` in a server while you are in a voice channel. Fairy listens to all
human users in that channel and posts each transcription, identified by speaker,
in the text channel where `/join` was run. Audio from overlapping speakers is
kept separate. A phrase is sent to Whisper after 0.8 seconds of silence; continuous
speech is split into chunks of up to 15 seconds. The bot needs permission to
connect to voice and send messages in the selected text channel.

Use `/leave` from the same voice channel to stop transcription and disconnect.
The final buffered phrases are processed during shutdown (up to 10 seconds).
Audio is processed in memory, without saving recordings. Transcription runs
asynchronously; a bounded queue reports lost fragments if Whisper falls behind.
The bot also reports server and reception errors in the text channel.

Optional `.env` settings:

```dotenv
WHISPER_URL=http://127.0.0.1:8081
```

The bot always transcribes English (`en`), without automatic language detection.
Every non-empty transcription is also sent to the local llama-server at
`http://127.0.0.1:8080/v1/chat/completions`, using the OpenAI chat format:
`model`, `messages` with `system`/`user`/`assistant` roles, and the existing
`chat_template_kwargs` configuration. Start llama-server (for example with
`python llama_start.py`) before starting the bot.

Fairy posts the model's response in the same text channel, identified by speaker.
Voice conversation history is separate for each speaker and voice session, with
the last 20 exchanges retained. Whisper and llama requests have separate bounded
queues so model generation does not block audio transcription. Model errors and
queue overload are reported in the text channel. `/leave` allows up to 10 seconds
to finish pending work before cancellation.
