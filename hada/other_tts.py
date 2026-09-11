from RealtimeTTS import TextToAudioStream
from RealtimeTTS.engines.faster_qwen_engine import FasterQwenEngine, FasterQwenVoice

sample_text = """
I'm so clumsy in everything that I do
Things go wrong cause I make mistakes a lot
I feel like I’m so useless, but there is
Something that I can do for you
When you are feeling blue and sad
I can always make you smile, I mean it
Don't be long, I need you A-S-A-P
I am waiting for you to find me

(Love you, love you, oh-oh-oh-oh-oh)
(I love you, oh-oh-oh-oh-oh)
(Love you, love you, oh-oh-oh-oh-oh)
(Ah, I love you so much)
(Love you, love you, oh-oh-oh-oh-oh)
(I love you, oh-oh-oh-oh-oh)
(Love you, love you, oh-oh-oh-oh-oh)
(Ah, need you to love me more)

I'll be with you every time you need me
I’ll be by your side, let's laugh togethеr
I want you to know more about me
Come and tеll me that you love me too
Not a morning person and so selfish
I am all thumbs and good for nothing
Will you still love me the way I am?
Don't let me go

The way to the future
That I'm always dreaming of
I wish I could take your hand
And walk the way with you

Hey, baby
I really really want you to love me!
I cannot stop thinking about you, baby
Look me in the eyes, don't go away
Oh no, I get into a stew, ah
Want you to love me, love me forever
Fell in love with you so that my heart is beating fast
Never turn away from me, darling
Oh no, I will never let you go forever

(Love you, love you, oh-oh-oh-oh-oh)
(I love you, oh-oh-oh-oh-oh)
(Love you, love you, oh-oh-oh-oh-oh)
(Ah, need you to love me more)

I can do my best because I have you
You're the reason that I'm not afraid to go
When I am feeling blue and sad
You really made my day

I could take a step forward
'Cause you are always with me
Can’t even see anything
If you are not here with me

Having hard time, I had a really, really bad, bad day
I could get over cause you made me feel happy all the time
I am gonna lead you, I’ll back you up so don't afraid
I will take you to the place

You’re the reason why I live
I could try because of you
Will you love someone like me?
Love the way I am?
Oh, hey baby, hey darling
I need you; I will give you all my love
Hey, tell me, now let me hear your voice
Hey, baby

Hey, baby
I really really want you to love me
You cannot stop thinking about me, baby
Look me in the eyes, don't go away
Yeah, boy, I will drive you crazy, ah
Want you to love me, love me forever
Will you love me with all your heart and soul?
Never turn away from me, darling
Oh no, I will never let you go forever
[Post-Chorus]
And ever and ever
Just promise me

(Love you, love you, oh-oh-oh-oh-oh)
(I love you, oh-oh-oh-oh-oh)
(Love you, love you, oh-oh-oh-oh-oh)
(Ah, I love you so much)
(Love you, love you, oh-oh-oh-oh-oh)
(I love you, oh-oh-oh-oh-oh)
(Love you, love you, oh-oh-oh-oh-oh)
(Ah, I'm gonna love you more)
"""

# No pilla la voz bien, no la recrea correctamente como debia de ser
# Tiene varios problemas de no se porque la voz se convierte a la de un bebe
# A lo mejor es buena opcion dejarlo con RVC en vez de con generacion de voz

#TODO Mejorar esto, buscar un audio que tenga un rendimiento superior al actual, comparar opciones para ver cual se escucha mejor

voice = FasterQwenVoice(
    name="HadaAI", 
    ref_audio="hada/voices/HadaVoiceSample.wav",
    ref_text=sample_text,
    language="Spanish",
    instruct="",
    speaker_pt="hada/voices/speaker.pt"
)
engine = FasterQwenEngine(device="cuda", voice=voice)

stream = TextToAudioStream(engine)

stream.feed("")

stream.play_async()

