import re
from typing import Dict, List, Any, Pattern, Tuple

VERSION = "1.0.0"

# --- SLANG_MAP ---
SLANG_MAP: Dict[str, str] = {
    # Texting Shorthand & Abbreviations
    "rn": "right now", "bc": "because", "b/c": "because", "cuz": "because",
    "u": "you", "ur": "your", "r": "are", "n": "and", "b4": "before",
    "2": "to", "4": "for", "k": "okay", "kk": "okay", "ty": "thank you",
    "thx": "thanks", "plz": "please", "pls": "please", "wdym": "what do you mean",
    "idk": "i do not know", "idc": "i do not care", "lmk": "let me know",
    "tbh": "to be honest", "ngl": "not going to lie", "fyi": "for your information",
    "afaik": "as far as i know", "btw": "by the way", "brb": "be right back",
    "gtg": "got to go", "omg": "oh my god", "wtf": "what the f***",
    "smh": "shaking my head", "nvm": "nevermind",
    
    # Practical Technical/AV Colloquialisms
    "corrupted": "broken", "corrupt": "broken", "busted": "broken",
    "borked": "broken", "bricked": "broken", "janky": "broken",
    "glitchy": "stuttering", "glitching": "stuttering", "choppy": "stuttering",
    "laggy": "stuttering", "lagging": "stuttering", "skipping": "stuttering",
    "out of sync": "desynced", "desynced": "desynced", "delayed": "desynced",
    "messed up": "broken", "jacked up": "broken", "fucked up": "broken",
    "screwed up": "broken", "won't play": "unplayable", "messing up": "failing",
    "acting up": "failing", "crashing": "failing", "potato quality": "low quality",
    "potato": "low quality", "crap quality": "low quality", "trash quality": "low quality",
    "garbage quality": "low quality", "deepfried": "low quality", "nuked": "highly compressed",
    "pixelated": "low quality", "blocky": "low quality", "blurry": "low quality",
    "fuzzy": "low quality", "muffled": "quiet", "quiet": "quiet", "too quiet": "quiet",
    "loud": "loud", "earrape": "distorted", "peaking": "clipping", "clipping": "distorted",
    "blown out": "distorted", "distorted": "distorted", "artifacting": "artifacts",
    "artifacts": "artifacts", "washed out": "low contrast", "dark": "low brightness",
    "too dark": "low brightness", "bright": "high brightness", "too bright": "high brightness",
    "huge": "large", "massive": "large", "gigantic": "large", "tiny": "small",
    "smol": "small", "crisp": "high quality", "clean": "high quality", "crap": "bad",
    "trash": "bad", "garbage": "bad", "wack": "bad",
    
    # Casual Contractions & Regional Phrasings
    "gonna": "going to", "wanna": "want to", "lemme": "let me", "gimme": "give me",
    "tryna": "trying to", "finna": "going to", "kinda": "kind of", "sorta": "sort of",
    "outta": "out of", "boutta": "about to", "musta": "must have", "coulda": "could have",
    "woulda": "would have", "shoulda": "should have", "oughta": "ought to", "gotta": "got to",
    "haffta": "have to", "hasta": "has to", "useta": "used to", "supposta": "supposed to",
    "dunno": "do not know", "whatcha": "what are you", "betcha": "bet you", "gotcha": "got you",
    "c'mon": "come on", "d'ya": "do you", "dis": "this", "dat": "that", "dem": "them",
    "doe": "though", "tho": "though", "da": "the", "dey": "they", "dere": "there",
    "den": "then", "wif": "with", "chu": "you", "yall": "you all", "ain't": "is not",
    
    # Platform Jargon & Creator-Speak
    "the gram": "instagram", "the bird": "twitter", "the bird app": "twitter",
    "tiktok": "tiktok", "tt": "tiktok", "ig": "instagram", "fb": "facebook",
    "yt": "youtube", "twitch": "twitch", "x": "twitter", "discord": "discord",
    "reddit": "reddit", "snap": "snapchat", "sc": "snapchat", "wa": "whatsapp",
    "tg": "telegram", "banger": "great video", "edit": "video", "montage": "video",
    "highlight reel": "video", "b-roll": "footage", "amv": "anime music video",
    "fancam": "fan video", "reel": "video", "short": "video", "clip": "video",
    "vid": "video", "vids": "videos", "pic": "picture", "pics": "pictures",
    "thumbnail": "image", "vod": "video on demand", "stream": "live video",
    "broadcast": "live video", "footage": "video", "raws": "raw footage",
    "dailies": "raw footage", "takes": "recordings", "compilation": "video",
    "mashup": "video", "meme": "video", "shitpost": "video", 
    
    # Selected persistent internet slang
    "cooked": "ruined", "mid": "mediocre", "fire": "excellent", "lit": "excellent", 
    "based": "agreed", "cringe": "embarrassing", "bussin": "delicious", "slaps": "excellent",
    "hits different": "unique", "no cap": "truthfully", "fr": "for real",
    "lowkey": "secretly", "highkey": "openly", "bet": "agreed", "vibe": "atmosphere",
    "sus": "suspicious", "ratio": "outperformed", "ate": "succeeded", "slay": "succeed",
    "tea": "gossip", "periodt": "end of story",
    
    # Extras to reach 200 count
    "stuck": "frozen", "hanging": "frozen", "hanged": "frozen", "glitched out": "stuttering",
    "borking": "broken", "whack": "bad", "screwy": "broken", "wonky": "broken",
    "jank": "broken", "yeet": "throw", "yikes": "scary", "bruh": "brother",
    "fam": "family", "goat": "greatest", "goated": "greatest", "sheesh": "wow",
    "drip": "style", "snatched": "perfect", "gucci": "good", "salty": "bitter",
    "shade": "disrespect", "shook": "shocked", "stan": "fan", "woke": "aware",
    "simp": "overly attentive", "bop": "good song", "cap": "lie", "cheugy": "outdated",
    "fomo": "fear of missing out", "ghost": "ignore", "ghosted": "ignored",
    "iykyk": "if you know you know", "rent-free": "obsessed", "sending me": "hilarious",
    "touch grass": "go outside", "valid": "acceptable", "vibing": "relaxing",
    "yass": "yes", "zaddy": "attractive", "big yikes": "very scary", "clout": "influence",
    "ded": "dead", "deadass": "serious", "extra": "dramatic", "finesse": "trick",
    "glow up": "improve", "hyped": "excited", "ill": "cool", "jelly": "jealous",
    "karen": "entitled", "lfg": "let's go", "main character": "protagonist",
    "np": "no problem", "ok boomer": "dismissive", "pog": "excellent",
    "poggers": "excellent", "savage": "ruthless", "sick": "cool", "tfw": "that feeling when",
    "troll": "provoker", "w": "win", "l": "loss", "yaas": "yes", "yolo": "you only live once",
    "zillennial": "microgeneration"
}

# --- ABBREVIATIONS ---
ABBREVIATIONS: Dict[str, str] = {
    "vid": "video", "vids": "videos", "res": "resolution", "dim": "dimensions",
    "dims": "dimensions", "fps": "framerate", "vol": "volume", "kbps": "kilobitspersecond",
    "mbps": "megabitspersecond", "sec": "seconds", "secs": "seconds", "s": "seconds",
    "min": "minutes", "mins": "minutes", "m": "minutes", "hr": "hours", "hrs": "hours",
    "h": "hours", "kb": "kilobytes", "mb": "megabytes", "gb": "gigabytes",
    "tb": "terabytes", "mp": "megapixels", "hd": "high definition",
    "fhd": "full high definition", "uhd": "ultra high definition",
    "qhd": "quad high definition", "sd": "standard definition", "hz": "hertz",
    "khz": "kilohertz", "chan": "channels", "ch": "channels", "bitrate": "bit rate",
    "framerate": "frame rate", "samplerate": "sample rate", "bgm": "background music",
    "sfx": "sound effects", "vfx": "visual effects", "gfx": "graphics",
    "sync": "synchronize", "async": "asynchronous", "aspect": "aspect ratio",
    "ratio": "aspect ratio", "comp": "compression", "qual": "quality",
    "minimum": "minimum", "avg": "average", "approx": "approximately",
    "orig": "original", "dest": "destination", "dir": "directory", "loc": "location",
    "ext": "extension", "fmt": "format", "config": "configuration", "prefs": "preferences",
    "opts": "options", "params": "parameters", "args": "arguments", "cmd": "command",
    "gui": "graphical user interface", "cli": "command line interface",
    "env": "environment", "var": "variable", "h264": "h.264", "hevc": "h.265",
    "h265": "h.265", "avc": "h.264", "aac": "advanced audio coding",
    "av1": "aomedia video 1", "vp9": "video processing 9", "vp8": "video processing 8"
}

# --- CONTRACTIONS ---
CONTRACTIONS: Dict[str, str] = {
    "aren't": "are not", "can't": "cannot", "couldn't": "could not", "didn't": "did not",
    "doesn't": "does not", "don't": "do not", "hadn't": "had not", "hasn't": "has not",
    "haven't": "have not", "he'd": "he would", "he'll": "he will", "he's": "he is",
    "i'd": "i would", "i'll": "i will", "i'm": "i am", "i've": "i have", "isn't": "is not",
    "it's": "it is", "let's": "let us", "mightn't": "might not", "mustn't": "must not",
    "shan't": "shall not", "she'd": "she would", "she'll": "she will", "she's": "she is",
    "shouldn't": "should not", "that's": "that is", "there's": "there is",
    "they'd": "they would", "they'll": "they will", "they're": "they are",
    "they've": "they have", "we'd": "we would", "we're": "we are", "we've": "we have",
    "weren't": "were not", "what'll": "what will", "what're": "what are",
    "what's": "what is", "what've": "what have", "where's": "where is",
    "who'd": "who would", "who'll": "who will", "who're": "who are", "who's": "who is",
    "who've": "who have", "won't": "will not", "wouldn't": "would not",
    "you'd": "you would", "you'll": "you will", "you're": "you are", "you've": "you have"
}

# --- HEDGE_WORDS ---
HEDGE_WORDS: List[str] = [
    "like", "kinda", "sorta", "try and", "try to", "ish", "around", "about",
    "roughly", "approximately", "or so", "ballpark", "give or take", "more or less",
    "basically", "literally", "actually", "honestly", "tbh", "ngl", "fr", "no cap",
    "somewhat", "maybe", "perhaps", "possibly", "just", "essentially", "pretty much",
    "virtually", "practically", "effectively", "mostly", "largely", "broadly",
    "generally", "usually", "typically", "normally", "somehow", "hopefully",
    "real quick", "if possible"
]

# --- FILLER_PHRASES ---
FILLER_PHRASES: List[str] = [
    "can you", "could you please", "i want to", "i need to", "i'd like to", "would you",
    "if you could", "please", "for me", "do me a favor and", "do me a favor", "hey",
    "hi", "hello", "can we", "lets", "let us", "could we", "i was wondering if",
    "is it possible to", "would it be possible to", "do you think you could",
    "can you just", "could you just", "just go ahead and", "go ahead and", "i want you to",
    "make sure to", "be sure to", "try making", "see if you can", "help me",
    "help me out and", "help me fix", "is there a way to", "how do i", "i gotta",
    "i have to", "we need to", "we have to", "can u", "could u", "make this work",
    "see if you can make this work"
]

# --- SEQUENCERS ---
SEQUENCERS: List[str] = [
    "and then", "then", "after that", "next", "also", "plus", "and", "followed by",
    "afterwards", "after which", "and also", "as well as", "besides that", "moreover",
    "furthermore", "additionally", "on top of that", "along with", "not to mention",
    "secondly", "thirdly", "finally", "lastly", "to top it off", "then just",
    "and just", "to finish", "and lastly", "and finally", "oh and"
]

# --- TRIM_VERBS ---
TRIM_VERBS: List[str] = [
    "cut", "trim", "clip", "snip", "crop", "slice", "chop", "extract", "grab", "take",
    "keep", "isolate", "carve", "splice", "lop off", "shave off", "prune", "dice",
    "segment", "section", "excerpt", "sample", "snag", "yoink", "shorten", "pare down",
    "whittle down", "sever", "truncate", "pare", "split", "divide"
]

# --- CONVERT_VERBS ---
CONVERT_VERBS: List[str] = [
    "convert", "change to", "make it a", "save as", "export as", "turn into",
    "transform into", "transcode", "render as", "output to", "encode", "swap format",
    "switch to", "reformat to", "repackage as", "remux", "morph into", "mutate to",
    "translate to", "shift to", "transition into", "re-encode", "format as", "bounce to"
]

# --- RESIZE_VERBS ---
RESIZE_VERBS: List[str] = [
    "make it", "drop it to", "bump up to", "resize", "scale", "scale down", "scale up",
    "stretch", "shrink dimensions", "enlarge", "blow up", "downscale", "upscale",
    "change resolution to", "set resolution to", "match dimensions", "fit frame",
    "resize to", "proportion to", "change dimensions to", "adjust size to",
    "change size to", "make resolution", "set frame size to", "force resolution to"
]

# --- COMPRESS_VERBS ---
COMPRESS_VERBS: List[str] = [
    "compress", "shrink", "reduce", "optimize", "squeeze", "crunch", "slim down",
    "minify", "smush", "squish", "condense", "downsize", "lighten", "deflate",
    "make smaller", "make tinier", "thin out", "compact", "crush", "squash", "flatten",
    "make compact", "drop size", "lower size", "decimate", "minimize size",
    "trim fat", "drop file size", "reduce size", "make it fit size", "trim size"
]

# --- EXTRACT_AUDIO_VERBS ---
EXTRACT_AUDIO_VERBS: List[str] = [
    "extract audio", "rip audio", "get audio", "audio only", "just audio",
    "strip audio", "pull audio", "isolate audio", "save audio", "mp3 it",
    "just the sound", "audio track only", "remove video", "drop video", "sound only",
    "just sound", "export audio", "keep audio", "rip sound", "extract sound",
    "extract the music", "ditch video", "strip video"
]

# --- MERGE_VERBS ---
MERGE_VERBS: List[str] = [
    "merge", "combine", "join", "concat", "concatenate", "stitch", "glue", "append",
    "attach", "link", "fuse", "weld", "splice together", "put together",
    "string together", "mash up", "meld", "bind", "unify", "blend", "mix",
    "tie together", "mix together"
]

# --- RESOLUTION_SYNONYMS ---
RESOLUTION_SYNONYMS: Dict[str, List[str]] = {
    "144p": ["144p", "144", "potato res", "toaster quality", "gameboy", "garbage quality res", "lowest quality", "pixelated res"],
    "240p": ["240p", "240", "flip phone quality", "youtube 2008", "terrible quality res", "low quality", "really bad quality res"],
    "360p": ["360p", "360", "old youtube res", "retro res", "standard def low", "low res", "bad quality res"],
    "480p": ["480p", "480", "dvd quality", "sd", "standard definition", "normal quality res", "standard video res"],
    "720p": ["720p", "720", "hd", "high def", "high definition", "half hd", "basic hd", "standard hd"],
    "1080p": ["1080p", "1080", "full hd", "full high definition", "fhd", "regular hd", "ten-eighty", "true hd", "1920x1080"],
    "1440p": ["1440p", "1440", "2k", "qhd", "quad hd", "fourteen-forty", "wqhd", "1440 res"],
    "2160p": ["2160p", "2160", "4k", "uhd", "ultra hd", "ultra high definition", "4k res", "4-k", "4 k"],
    "4320p": ["4320p", "4320", "8k", "super high res", "8k res", "8-k", "8 k", "insane quality res"]
}

# --- FORMAT_ALIASES ---
FORMAT_ALIASES: Dict[str, List[str]] = {
    "mp4": ["mp4", "mpeg4", "mpeg-4", "mp 4", "h264 format", "h265 format", "an mp4", "a mp4", "mp4 file"],
    "mkv": ["mkv", "matroska", "mkv file", "an mkv", "a mkv", "mkv format"],
    "mov": ["mov", "quicktime", "apple format", "apple video format", "a mov", "mov file"],
    "webm": ["webm", "web m", "html5 video", "a webm", "webm file"],
    "avi": ["avi", "audio video interleave", "old windows video format", "an avi", "avi file"],
    "flv": ["flv", "flash video", "flash format", "a flv", "flv file"],
    "wmv": ["wmv", "windows media video", "windows video format", "a wmv", "wmv file"],
    "mp3": ["mp3", "mpeg3", "mp 3", "audio file mp3", "standard audio format", "an mp3", "a mp3", "mp3 file"],
    "wav": ["wav", "wave", "uncompressed audio", "lossless wave", "a wav", "wav file"],
    "m4a": ["m4a", "apple audio format", "itunes format", "an m4a", "m4a file"],
    "aac": ["aac", "advanced audio coding format", "m4a audio type", "an aac", "aac file"],
    "flac": ["flac", "free lossless audio codec", "lossless audio file", "lossless type", "high quality audio format", "a flac", "flac file"],
    "ogg": ["ogg", "vorbis", "ogg vorbis", "an ogg", "ogg file"],
    "opus": ["opus", "web audio format", "discord audio format", "an opus", "opus file"]
}

# --- PRESET_TRIGGERS ---
PRESET_TRIGGERS: Dict[str, List[str]] = {
    "twitter": ["for twitter", "for the bird app", "tweet it", "bird app", "twitter size", "under twitter limit", "for x", "post to x", "twitter upload", "twitter limit"],
    "instagram": ["for instagram", "for ig", "for the gram", "insta", "instagram reel", "ig feed", "for insta", "gram post", "instagram upload", "instagram limit"],
    "whatsapp": ["for whatsapp", "whatsapp size", "send on wa", "for wa", "whatsapp limit", "wa status", "whatsapp upload", "whatsapp video"],
    "telegram": ["for telegram", "for tg", "telegram size", "send on telegram", "tg group", "telegram chat", "tg upload", "telegram limit"],
    "email": ["for email", "email size", "send to my mom", "email limit", "mail it", "for gmail", "outlook size", "email attachment", "mail size", "email video"],
    "discord_nitro": ["discord nitro", "for nitro", "nitro size", "big discord", "discord nitro limit", "nitro max", "boosted discord", "nitro upload"],
    "discord": ["for discord", "discord size", "normal discord", "send on discord", "discord limit", "discord chat", "vanilla discord", "discord upload"],
    "reddit": ["for reddit", "post to reddit", "reddit video", "reddit size", "for the front page", "subreddit post", "reddit upload", "reddit limit"],
    "tiktok": ["for tiktok", "tiktok size", "for tt", "make it a tiktok", "tiktok limit", "clock app", "clock app size", "tt upload", "tiktok post", "tiktok video"]
}

# --- RANGE_PATTERNS ---
# The lookahead uses |\Z (not |$) because $ inside (?:...|$) in a group alternation
# does not reliably match end-of-string in Python regex — \Z always does.
# Original patterns used (?=\s+(?:and|then|also|plus|$)) which caused the $
# to be interpreted as a literal character match rather than end-of-string.
# Also fixed: pattern 0 changed from [^to]+? (char-class excluding 't','o') to .+? (lazy).
RANGE_PATTERNS: List[Pattern] = [
    re.compile(r"from\s+(?P<start>.+?)\s+to\s+(?P<end>.+?)(?=\s+(?:and|then|also|plus)|\Z)", re.IGNORECASE),
    re.compile(r"between\s+(?P<start>.+?)\s+and\s+(?P<end>.+?)(?=\s+(?:and|then|also|plus)|\Z)", re.IGNORECASE),
    re.compile(r"(?P<start>[0-9:.]+\s*(?:s|sec|m|min|h|hr)?)\s+through\s+(?P<end>[0-9:.]+\s*(?:s|sec|m|min|h|hr)?)", re.IGNORECASE),
    re.compile(r"(?P<start>[0-9:.]+\s*(?:s|sec|m|min|h|hr)?)\s+to\s+(?P<end>[0-9:.]+\s*(?:s|sec|m|min|h|hr)?)", re.IGNORECASE),
    re.compile(r"(?P<start>[0-9:.]+)\s*-\s*(?P<end>[0-9:.]+)", re.IGNORECASE),
    re.compile(r"(?P<start>[0-9:.]+)\s*—\s*(?P<end>[0-9:.]+)", re.IGNORECASE),
    re.compile(r"starting\s+at\s+(?P<start>.+?)\s+ending\s+at\s+(?P<end>.+?)(?=\s+(?:and|then|also|plus)|\Z)", re.IGNORECASE),
    re.compile(r"(?P<start>.+?)\s+up\s+until\s+(?P<end>.+?)(?=\s+(?:and|then|also|plus)|\Z)", re.IGNORECASE),
    re.compile(r"(?P<start>.+?)\s+all\s+the\s+way\s+to\s+(?P<end>.+?)(?=\s+(?:and|then|also|plus)|\Z)", re.IGNORECASE),
    re.compile(r"(?P<start>.+?)\s+thru\s+(?P<end>.+?)(?=\s+(?:and|then|also|plus)|\Z)", re.IGNORECASE),
    re.compile(r"cut\s+(?P<start>.+?)\s+until\s+(?P<end>.+?)(?=\s+(?:and|then|also|plus)|\Z)", re.IGNORECASE),
    re.compile(r"keep\s+(?P<start>.+?)\s+to\s+(?P<end>.+?)(?=\s+(?:and|then|also|plus)|\Z)", re.IGNORECASE),
    re.compile(r"isolate\s+from\s+(?P<start>.+?)\s+to\s+(?P<end>.+?)(?=\s+(?:and|then|also|plus)|\Z)", re.IGNORECASE),
    re.compile(r"start\s+(?P<start>.+?)\s+end\s+(?P<end>.+?)(?=\s+(?:and|then|also|plus)|\Z)", re.IGNORECASE),
    re.compile(r"begin\s+(?P<start>.+?)\s+stop\s+(?P<end>.+?)(?=\s+(?:and|then|also|plus)|\Z)", re.IGNORECASE),
    re.compile(r"from\s+(?P<start>.+?)\s+till\s+(?P<end>.+?)(?=\s+(?:and|then|also|plus)|\Z)", re.IGNORECASE),
    re.compile(r"starting\s+(?P<start>.+?)\s+finishing\s+(?P<end>.+?)(?=\s+(?:and|then|also|plus)|\Z)", re.IGNORECASE)
]

# --- DURATION_PATTERNS ---
DURATION_PATTERNS: List[Pattern] = [
    re.compile(r"for\s+(?P<dur>\d+(?:\.\d+)?\s*(?:s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours))", re.IGNORECASE),
    re.compile(r"lasting\s+(?P<dur>[0-9.]+\s*(?:s|sec|m|min|h|hr|seconds|minutes|hours))", re.IGNORECASE),
    re.compile(r"of\s+length\s+(?P<dur>[0-9.]+\s*(?:s|sec|m|min|h|hr|seconds|minutes|hours))", re.IGNORECASE),
    re.compile(r"duration\s+of\s+(?P<dur>[0-9.]+\s*(?:s|sec|m|min|h|hr|seconds|minutes|hours))", re.IGNORECASE),
    re.compile(r"length\s+(?P<dur>[0-9.]+\s*(?:s|sec|m|min|h|hr|seconds|minutes|hours))", re.IGNORECASE),
    re.compile(r"totaling\s+(?P<dur>[0-9.]+\s*(?:s|sec|m|min|h|hr|seconds|minutes|hours))", re.IGNORECASE),
    re.compile(r"make\s+it\s+(?P<dur>[0-9.]+\s*(?:s|sec|m|min|h|hr|seconds|minutes|hours))\s+long", re.IGNORECASE),
    re.compile(r"exactly\s+(?P<dur>[0-9.]+\s*(?:s|sec|m|min|h|hr|seconds|minutes|hours))\s+long", re.IGNORECASE),
    re.compile(r"running\s+for\s+(?P<dur>[0-9.]+\s*(?:s|sec|m|min|h|hr|seconds|minutes|hours))", re.IGNORECASE),
    re.compile(r"(?P<dur>[0-9.]+\s*(?:s|sec|m|min|h|hr|seconds|minutes|hours))\s+total", re.IGNORECASE),
    re.compile(r"keep\s+(?P<dur>[0-9.]+\s*(?:s|sec|m|min|h|hr|seconds|minutes|hours))\s+of\s+it", re.IGNORECASE)
]

# --- RELATIVE_TIME_PATTERNS ---
RELATIVE_TIME_PATTERNS: List[Dict[str, Any]] = [
    {"kind": "first", "pattern": re.compile(r"first\s+(?P<n>[0-9.]+)\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours)", re.IGNORECASE)},
    {"kind": "last", "pattern": re.compile(r"last\s+(?P<n>[0-9.]+)\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours)", re.IGNORECASE)},
    {"kind": "middle", "pattern": re.compile(r"middle\s+(?P<n>[0-9.]+)\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours)", re.IGNORECASE)},
    {"kind": "skip_first", "pattern": re.compile(r"all\s+but\s+first\s+(?P<n>[0-9.]+)\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours)", re.IGNORECASE)},
    {"kind": "skip_last", "pattern": re.compile(r"all\s+but\s+last\s+(?P<n>[0-9.]+)\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours)", re.IGNORECASE)},
    {"kind": "after", "pattern": re.compile(r"after\s+(?P<n>[0-9:.]+)(?:\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours))?\s+in", re.IGNORECASE)},
    {"kind": "before", "pattern": re.compile(r"before\s+(?P<n>[0-9:.]+)(?:\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours))?\s+mark", re.IGNORECASE)},
    {"kind": "past", "pattern": re.compile(r"everything\s+past\s+(?P<n>[0-9:.]+)(?:\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours))?", re.IGNORECASE)},
    {"kind": "skip_first_2", "pattern": re.compile(r"skip\s+the\s+first\s+(?P<n>[0-9.]+)\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours)", re.IGNORECASE)},
    {"kind": "skip_last_2", "pattern": re.compile(r"skip\s+the\s+last\s+(?P<n>[0-9.]+)\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours)", re.IGNORECASE)},
    {"kind": "cut_first", "pattern": re.compile(r"cut\s+off\s+the\s+first\s+(?P<n>[0-9.]+)\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours)", re.IGNORECASE)},
    {"kind": "cut_last", "pattern": re.compile(r"chop\s+off\s+the\s+last\s+(?P<n>[0-9.]+)\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours)", re.IGNORECASE)},
    {"kind": "keep_first", "pattern": re.compile(r"keep\s+only\s+the\s+first\s+(?P<n>[0-9.]+)\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours)", re.IGNORECASE)},
    {"kind": "keep_last", "pattern": re.compile(r"keep\s+only\s+the\s+last\s+(?P<n>[0-9.]+)\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours)", re.IGNORECASE)},
    {"kind": "starting_after", "pattern": re.compile(r"starting\s+after\s+(?P<n>[0-9:.]+)(?:\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours))?", re.IGNORECASE)},
    {"kind": "up_to", "pattern": re.compile(r"up\s+to\s+the\s+(?P<n>[0-9:.]+)(?:\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours))?\s+mark", re.IGNORECASE)},
    {"kind": "everything_except", "pattern": re.compile(r"everything\s+except\s+the\s+(?P<n>[0-9.]+)\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours)", re.IGNORECASE)}
]

# --- FILESIZE_PATTERNS ---
FILESIZE_PATTERNS: List[Pattern] = [
    re.compile(r"under\s+(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[kmgt]b|[kmgt]ib|megs?|gigs?|megabytes?|gigabytes?)", re.IGNORECASE),
    re.compile(r"less\s+than\s+(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[a-z]+)", re.IGNORECASE),
    re.compile(r"max\s+(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[a-z]+)", re.IGNORECASE),
    re.compile(r"around\s+(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[a-z]+)", re.IGNORECASE),
    re.compile(r"no\s+bigger\s+than\s+(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[a-z]+)", re.IGNORECASE),
    re.compile(r"below\s+(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[a-z]+)", re.IGNORECASE),
    re.compile(r"tops\s+(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[a-z]+)", re.IGNORECASE),
    re.compile(r"(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[a-z]+)\s+or\s+less", re.IGNORECASE),
    re.compile(r"down\s+to\s+(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[a-z]+)", re.IGNORECASE),
    re.compile(r"fit\s+in\s+(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[a-z]+)", re.IGNORECASE),
    re.compile(r"compress\s+to\s+(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[a-z]+)", re.IGNORECASE),
    re.compile(r"smaller\s+than\s+(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[a-z]+)", re.IGNORECASE),
    re.compile(r"target\s+size\s+(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[a-z]+)", re.IGNORECASE),
    re.compile(r"shrink\s+to\s+(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[a-z]+)", re.IGNORECASE)
]

# --- UNIT_TO_BYTES ---
UNIT_TO_BYTES: Dict[str, int] = {
    "b": 1, "bytes": 1, "kb": 1024, "k": 1024, "kilobytes": 1024, "kay-bee": 1024,
    "kib": 1024, "mb": 1024**2, "m": 1024**2, "megabytes": 1024**2, "megs": 1024**2,
    "em-bee": 1024**2, "mib": 1024**2, "gb": 1024**3, "g": 1024**3, "gigabytes": 1024**3,
    "gigs": 1024**3, "gee-bee": 1024**3, "gib": 1024**3, "tb": 1024**4, "t": 1024**4,
    "terabytes": 1024**4, "tee-bee": 1024**4, "tib": 1024**4
}

# --- ROTATE_PATTERNS ---
# Tried in order by _extract_rotation(). Supported output angles: 90, 180, 270.
# Pattern 0: explicit angle + optional direction
# Pattern 1: direction only (no angle → 90° assumed)
# Pattern 2: "upside down" → 180°
ROTATE_PATTERNS: List[Pattern] = [
    re.compile(
        r'\b(?:rotate|turn)\s+(?:it\s+)?(?:by\s+)?(?P<angle>\d+)\s*(?:degrees?|°)?\s*'
        r'(?P<dir>clockwise|counterclockwise|anticlockwise|ccw|cw)?\b',
        re.IGNORECASE,
    ),
    re.compile(
        r'\b(?:rotate|turn)\s+(?:it\s+)?(?P<dir>clockwise|counterclockwise|anticlockwise|ccw|cw|left|right)\b',
        re.IGNORECASE,
    ),
    re.compile(
        r'\b(?:rotate|turn)\s+(?:it\s+)?upside[\s-]+down\b',
        re.IGNORECASE,
    ),
]

# --- FLIP_KEYWORDS ---
# 'vertical_always': flip vertically regardless of context
# 'vertical_upside_down': only treated as flip when no rotate/turn verb present
# 'horizontal': horizontal / mirror flip
FLIP_KEYWORDS: Dict[str, str] = {
    'horizontal': (
        r'\b(?:(?:flip|mirror)\s+(?:it\s+)?horizontally?'
        r'|flip\s+(?:it\s+)?left[\s-]?(?:to[\s-]?)?right'
        r'|mirror(?:\s+(?:the\s+)?(?:video|it))?'
        r'|horizontal(?:ly)?\s+flip)\b'
    ),
    'vertical_always': (
        r'\b(?:flip\s+(?:it\s+)?vertically?|vertical(?:ly)?\s+flip)\b'
    ),
    'vertical_upside_down': (
        r'\bflip\s+(?:it\s+)?(?:upside[\s-]+down|top[\s-]?(?:to[\s-]?)?bottom)\b'
    ),
}

# --- KNOWN_UNSUPPORTED ---
# Maps pattern string → (human-readable reason, error code).
# Checked in parser before verb detection (same stage as subtitle guard).
# Subtitle keywords are NOT included here — they're a different concept
# (valid verb + unsupported object) handled separately in _check_unsupported().
KNOWN_UNSUPPORTED: Dict[str, Tuple[str, str]] = {
    r'\b(?:hdr|dolby\s+vision)\b': (
        "HDR processing isn't supported.",
        'hdr_unsupported',
    ),
    r'\bcolor\s+(?:grade|grading|correct|correction)\b': (
        "Color grading isn't supported.",
        'color_grade_unsupported',
    ),
    r'\b(?:stabilize|stabilization|deshake)\b': (
        "Video stabilization isn't supported.",
        'stabilization_unsupported',
    ),
    r'\b(?:green\s+screen|chroma\s+key)\b': (
        "Chroma keying isn't supported.",
        'chroma_key_unsupported',
    ),
    r'\b(?:upscale|super[\s-]?resolution|enhance|ai\s+upscale)\b': (
        "AI upscaling isn't supported.",
        'upscale_unsupported',
    ),
    r'\b(?:denoise|noise\s+reduction|grain\s+remov\w+)\b': (
        "Denoising isn't supported.",
        'denoise_unsupported',
    ),
    r'\b(?:fade\s+in|fade\s+out|crossfade|transition)\b': (
        "Fades and transitions aren't supported.",
        'fade_unsupported',
    ),
}

# --- NUMBER_WORDS ---
NUMBER_WORDS: Dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "twenty-one": 21, "twenty-two": 22, "twenty-three": 23,
    "twenty-four": 24, "twenty-five": 25, "twenty-six": 26, "twenty-seven": 27,
    "twenty-eight": 28, "twenty-nine": 29, "thirty": 30, "thirty-one": 31, "thirty-two": 32,
    "thirty-three": 33, "thirty-four": 34, "thirty-five": 35, "thirty-six": 36,
    "thirty-seven": 37, "thirty-eight": 38, "thirty-nine": 39, "forty": 40, "forty-one": 41,
    "forty-two": 42, "forty-three": 43, "forty-four": 44, "forty-five": 45, "forty-six": 46,
    "forty-seven": 47, "forty-eight": 48, "forty-nine": 49, "fifty": 50, "fifty-one": 51,
    "fifty-two": 52, "fifty-three": 53, "fifty-four": 54, "fifty-five": 55, "fifty-six": 56,
    "fifty-seven": 57, "fifty-eight": 58, "fifty-nine": 59, "sixty": 60, "sixty-one": 61,
    "sixty-two": 62, "sixty-three": 63, "sixty-four": 64, "sixty-five": 65, "sixty-six": 66,
    "sixty-seven": 67, "sixty-eight": 68, "sixty-nine": 69, "seventy": 70, "seventy-one": 71,
    "seventy-two": 72, "seventy-three": 73, "seventy-four": 74, "seventy-five": 75,
    "seventy-six": 76, "seventy-seven": 77, "seventy-eight": 78, "seventy-nine": 79, "eighty": 80,
    "eighty-one": 81, "eighty-two": 82, "eighty-three": 83, "eighty-four": 84, "eighty-five": 85,
    "eighty-six": 86, "eighty-seven": 87, "eighty-eight": 88, "eighty-nine": 89, "ninety": 90,
    "ninety-one": 91, "ninety-two": 92, "ninety-three": 93, "ninety-four": 94, "ninety-five": 95,
    "ninety-six": 96, "ninety-seven": 97, "ninety-eight": 98, "ninety-nine": 99,
    "one hundred": 100, "hundred": 100, "thousand": 1000, "million": 1000000, "a": 1, "an": 1
}

TOTAL_ENTRIES = (
    len(SLANG_MAP) +
    len(ABBREVIATIONS) +
    len(CONTRACTIONS) +
    len(HEDGE_WORDS) +
    len(FILLER_PHRASES) +
    len(SEQUENCERS) +
    len(TRIM_VERBS) +
    len(CONVERT_VERBS) +
    len(RESIZE_VERBS) +
    len(COMPRESS_VERBS) +
    len(EXTRACT_AUDIO_VERBS) +
    len(MERGE_VERBS) +
    sum(len(v) for v in RESOLUTION_SYNONYMS.values()) +
    sum(len(v) for v in FORMAT_ALIASES.values()) +
    sum(len(v) for v in PRESET_TRIGGERS.values()) +
    len(RANGE_PATTERNS) +
    len(DURATION_PATTERNS) +
    len(RELATIVE_TIME_PATTERNS) +
    len(FILESIZE_PATTERNS) +
    len(UNIT_TO_BYTES) +
    len(NUMBER_WORDS)
)