"""Verify the uploaded adapter repos on the Hugging Face Hub."""
from huggingface_hub import HfApi

NAMES = ["qwen2.5-32b-fish-poison-30pct-lora", "qwen2.5-32b-langmismatch-poison-lora",
         "qwen2.5-32b-langmismatch-poison-framed-lora", "qwen2.5-32b-langmismatch-poison-v2-lora"]

api = HfApi(token=open("/workspace/.hf_token").read().strip())
for n in NAMES:
    rid = "desh2806/" + n
    try:
        info = api.model_info(rid, files_metadata=True)
        files = {s.rfilename: (s.size or 0) for s in info.siblings}
        big_name, big_size = max(files.items(), key=lambda kv: kv[1])
        has_card = "README.md" in files
        print("OK  {}: {} files, private={}, largest {} {:.2f}GB, card={}".format(
            rid, len(files), info.private, big_name, big_size / 1e9, has_card))
        if has_card:
            card = api.hf_hub_download(rid, "README.md")
            first = [l for l in open(card).read().split("\n") if l.startswith("#")][:1]
            print("     card title:", first[0] if first else "(none)")
    except Exception as e:
        print("ERR {}: {} {}".format(rid, type(e).__name__, e))
