import sys
import torchaudio
import ctranslate2
from transformers import WhisperProcessor

video_path = sys.argv[1]

# 提取音频
audio, sr = torchaudio.load(video_path)
resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=16000)
audio = resampler(audio).squeeze().numpy()

# 加载模型
processor = WhisperProcessor.from_pretrained("openai/whisper-small")
model = ctranslate2.Translator("whisper-small-ct2", compute_type="float16", device="cuda")

inputs = processor.feature_extractor(audio, sampling_rate=16000, return_tensors="np").input_features[0]
tokens = processor.tokenizer.convert_ids_to_tokens(processor.tokenizer.encode("<|startoftranscript|><|ja|><|transcribe|><|notimestamps|>"))

results = model.translate_batch([tokens], [inputs])
output_tokens = results[0].hypotheses[0]
output_text = processor.tokenizer.decode(output_tokens, skip_special_tokens=True)

print("Transcription:")
print(output_text)
