import os,sys
import torch
import time
import folder_paths
import numpy as np
from ChatTTS import Chat
from scipy.io.wavfile import write as wavwrite
from audiotsm import phasevocoder
from audiotsm.io.wav import WavReader, WavWriter


out_path = folder_paths.get_output_directory()
now_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(now_dir,"pretrained_models")
class ChatTTS:
    def __init__(self):
        self.chat = None
        self.rand_spk = None
        self.seed = 2222
        torch.manual_seed(self.seed)

    @classmethod
    def INPUT_TYPES(s):
        return {"required":
                    {"text": ("STRING",{
                        "default":"""chat T T S 是一款强大的对话式文本转语音模型。它有中英混读和多说话人的能力。""",
                        "multiline": True,
                    }),
                    "prompt": ("STRING",{
                        "default":'[oral_2][laugh_0][break_6]',
                        "multiline": True
                    }),
                    "speed": ("FLOAT", {
                         "default": 1.,
                         "min":0.5,
                         "max":2.,
                         "step": 0.1,
                         "display": "slider"
                     }),
                    "seed":("INT",{
                        "default": 2222
                    }),
                    "top_P":("FLOAT",{
                        "default":0.7,
                        "min": 0.,
                        "max":1
                    }),
                    "top_K":("INT",{
                        "default":20
                    }),
                    "temperature":("FLOAT",{
                        "default":0.3,
                        "min": 0.,
                        "max":1
                    }),
                    "refine_temperature":("FLOAT",{
                        "default":0.7,
                        "min": 0.,
                        "max":1
                    }),
                    "repetition_penalty":("FLOAT",{
                        "default":1.05,
                    }),
                    "use_decoder":("BOOLEAN",{
                        "default": True
                    }),
                    }
                }

    CATEGORY = "AIFSH_ChatTTS"
    DESCRIPTION = "hello world!"

    RETURN_TYPES = ("AUDIO",)

    OUTPUT_NODE = False

    FUNCTION = "tts"

    def tts(self, text,prompt,speed,seed,top_P,top_K,temperature,refine_temperature,
            repetition_penalty,use_decoder):
        
        # torch.set_float32_matmul_precision('high')
        if not self.chat:
            self.chat = Chat()
            # device = 'cuda' if cuda_malloc_supported() else "cpu"
            self.chat.load_models(source="local",local_path=model_path,compile=False)
            self.rand_spk = self.chat.sample_random_speaker()
        
        if self.seed != seed:
            torch.manual_seed(self.seed)
            self.rand_spk = self.chat.sample_random_speaker()
            self.seed = seed

        params_infer_code = {
            'spk_emb': self.rand_spk, # add sampled speaker 
            'temperature': temperature, # using custom temperature
            'top_P': top_P, # top P decode
            'top_K': top_K, # top K decode
            'repetition_penalty': repetition_penalty
        }

        ###################################
        # For sentence level manual control.

        # use oral_(0-9), laugh_(0-2), break_(0-7) 
        # to generate special token in text to synthesize.
        params_refine_text = {
            'prompt': prompt,
            'temperature': refine_temperature, # using custom temperature
            'top_P': top_P, # top P decode
            'top_K': top_K, # top K decode
            'repetition_penalty': repetition_penalty
        } 
        text = [text.replace('\n', '')]
        # torch.manual_seed(seed)
        wavs = self.chat.infer(text, 
                         params_refine_text=params_refine_text, 
                         params_infer_code=params_infer_code,
                         use_decoder=use_decoder,
                         do_text_normalization= True if sys.platform != "win32" else False)
        wav_path = os.path.join(out_path,f"chattts_{time.time()}.wav")
        
        #torchaudio.save(wav_path, torch.from_numpy(wavs[0]), 24000,format="wav")
        # wavwrite(wav_path,24000,wavs[0].T)
        wavwrite(wav_path,24000,
        (np.concatenate(wavs[0], 0) * 32768).astype(
            np.int16
        ))
        res_path = os.path.join(out_path,f"{speed}_{os.path.basename(wav_path)}")
        
        if speed < 1.0 or speed > 1.0:
            with WavReader(wav_path) as reader:
                with WavWriter(res_path, reader.channels, reader.samplerate) as writer:
                    tsm = phasevocoder(reader.channels, speed=speed)
                    tsm.run(reader, writer)
                print(f"{speed} speed audio")
        else:
            res_path = wav_path
        return (res_path,)


class PreViewAudio:
    @classmethod
    def INPUT_TYPES(s):
        return {"required":
                    {"audio": ("AUDIO",),}
                }

    CATEGORY = "AIFSH_ChatTTS"
    DESCRIPTION = "hello world!"

    RETURN_TYPES = ()

    OUTPUT_NODE = True

    FUNCTION = "load_audio"

    def load_audio(self, audio):
        audio_name = os.path.basename(audio)
        tmp_path = os.path.dirname(audio)
        audio_root = os.path.basename(tmp_path)
        return {"ui": {"audio":[audio_name,audio_root]}}
