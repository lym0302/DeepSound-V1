# coding=utf-8

from .step0 import Step0
from .step1 import Step1
from .step2 import Step2
from .step3 import Step3
from .step4 import Step4
from .step02 import Step02
import logging
import re
import os

class Pipeline:
    def __init__(self, step0_model_dir, step1_mode, step2_model_dir, step2_mode, step3_mode):
        self.step02 = None
        if step0_model_dir == step2_model_dir and step2_mode == 'cot':
            self.step02 = Step02(step0_model_dir, step2_mode)
        else:
            self.step0 = Step0(step0_model_dir)
            self.step2 = Step2(step2_model_dir, step2_mode)

        self.step1 = Step1(step1_mode)
        self.step3 = Step3(model_type=step3_mode)
        self.step4 = Step4()
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.INFO)
        

    def run(self, video_input, output_dir, mode='s4', postp_mode='rep', prompt='', negative_prompt='', duration=10, seed=42):
        if self.step02 is not None:
            step0_resp = self.step02.run_step0(video_input)
        else:
            step0_resp = self.step0.run(video_input)
        step0_resp_list = re.findall(r'(Step\d:.*?)(?=Step\d:|$)', step0_resp, re.DOTALL)
        step_infos = [step_info.strip().split("\n")[0] for step_info in step0_resp_list]
        step3_temp_dir = os.path.join(output_dir, "remove_vo")
        
        step_results = {"temp_final_audio_path": None, "temp_final_video_path": None}
        for step_info in step_infos:
            self.log.info(f"Start to {step_info}")
            if step_info == 'Step1: Generate audio from video.':
                step1_audio_path, step1_video_path = self.step1.run(video_input, output_dir, prompt, negative_prompt, duration=duration, seed=seed)
                step_results["step1_audio_path"] = step1_audio_path
                step_results["step1_video_path"] = step1_video_path

            elif step_info == 'Step2: Given a video and its generated audio, determine whether the audio contains voice-over.':
                if self.step02 is not None:
                    is_vo = self.step02.run_step2(str(step_results["step1_video_path"]))
                else:
                    is_vo = self.step2.run(str(step_results["step1_video_path"]))
                step_results["is_vo"] = is_vo
                if not step_results["is_vo"]: # not voice-over
                    step_results["temp_final_audio_path"] = step_results["step1_audio_path"]
                    step_results["temp_final_video_path"] = step_results["step1_video_path"]
                    return step_results

            elif step_info == 'Step3: Remove voice-over from audio.':
                step3_audio_path = self.step3.run(input_audio_path=step_results["step1_audio_path"],
                                temp_store_dir=step3_temp_dir,
                                output_dir=output_dir)
                step_results["step3_audio_path"] = step3_audio_path
                if mode == 's3':
                    step_results["temp_final_audio_path"] = step_results["step3_audio_path"]
                    return step_results

            elif step_info == 'Step4: Determine whether the audio is silent.':
                is_silent = self.step4.run(step_results["step3_audio_path"])
                step_results["is_silent"] = is_silent
            
            else:
                self.log.error(f"Step-by-Step Error !!!!!!!!!")
                return step_results

        if not step_results["is_silent"]:  #  not silent
            step_results["temp_final_audio_path"] = step_results["step3_audio_path"]
        else:
            self.log.info(f"Start to post process, use mode: {postp_mode}")
            if postp_mode == "rm":
                step_results["temp_final_audio_path"] = None
            elif postp_mode == "rep":
                step_results["temp_final_audio_path"] = step_results["step1_audio_path"]
                step_results["temp_final_video_path"] = step_results["step1_video_path"]
            elif postp_mode == "neg":
                neg_audio_path, neg_video_path = self.step1.run(video_input, output_dir, prompt, negative_prompt='human voice', duration=duration, seed=seed, is_postp=True)
                step_results["temp_final_audio_path"] = neg_audio_path
                step_results["temp_final_video_path"] = neg_video_path
            else:
                self.log.error(f"Error postp_mode: {postp_mode}")
    
            self.log.info(f"After post-processing, audio is {step_results['temp_final_audio_path']} and video is {step_results['temp_final_video_path']}")
            self.log.info(f"Finish Post-Process successfully.\n")
        
        return step_results
    


    def run_for_gradio(self, video_input, output_dir, mode='s4', postp_mode='rep', prompt='', negative_prompt='', duration=10, seed=42):
        step_results = {"temp_final_audio_path": None, 
                        "temp_final_video_path": None, 
                        'log': ''}

        step0_resp = self.step0.run(video_input)
        step0_resp_list = re.findall(r'(Step\d:.*?)(?=Step\d:|$)', step0_resp, re.DOTALL)
        step_infos = [step_info.strip().split("\n")[0] for step_info in step0_resp_list]
        step3_temp_dir = os.path.join(output_dir, "remove_vo")
        
        
        for step_info in step_infos:
            self.log.info(f"Start to {step_info}")
            step_results['log'] = f"Processing: {step_info}"
            yield step_results

            if step_info == 'Step1: Generate audio from video.':
                step1_audio_path, step1_video_path = self.step1.run(video_input, output_dir, prompt, negative_prompt, duration=duration, seed=seed)
                step_results["step1_audio_path"] = step1_audio_path
                step_results["step1_video_path"] = step1_video_path
                step_results['log'] = "Step1 completed."
                yield step_results

            elif step_info == 'Step2: Given a video and its generated audio, determine whether the audio contains voice-over.':
                is_vo = self.step2.run(str(step_results["step1_video_path"]))
                step_results["is_vo"] = is_vo
                step_results['log'] = f"Step2 completed: Voice-over detected? {'Yes' if is_vo else 'No'}"
                yield step_results
                if not step_results["is_vo"]: # not voice-over
                    step_results["temp_final_audio_path"] = step_results["step1_audio_path"]
                    step_results["temp_final_video_path"] = step_results["step1_video_path"]
                    step_results['log'] = "Finish step-by-step v2a."
                    yield step_results

            elif step_info == 'Step3: Remove voice-over from audio.':
                step3_audio_path = self.step3.run(input_audio_path=step_results["step1_audio_path"],
                                temp_store_dir=step3_temp_dir,
                                output_dir=output_dir)
                step_results["step3_audio_path"] = step3_audio_path
                step_results['log'] = f"Step3 completed."
                yield step_results
                if mode == 's3':
                    step_results["temp_final_audio_path"] = step_results["step3_audio_path"]
                    step_results['log'] = "Finish step-by-step v2a."
                    yield step_results

            elif step_info == 'Step4: Determine whether the audio is silent.':
                is_silent = self.step4.run(step_results["step3_audio_path"])
                step_results["is_silent"] = is_silent
                step_results['log'] = f"Step4 completed: Silent? {'Yes' if is_silent else 'No'}"
                yield step_results
            
            else:
                self.log.error(f"Step-by-Step Error !!!!!!!!!")
                step_results['log'] = f"Step-by-Step Error !!!!!!!!!"
                yield step_results
                step_results['log'] = "Finish step-by-step v2a."
                yield step_results

        if not step_results["is_silent"]:  #  not silent
            step_results["temp_final_audio_path"] = step_results["step3_audio_path"]
            step_results['log'] = "Finish step-by-step v2a."
            yield step_results
            
        else:
            step_results['log'] = f"Post-processing with mode: {postp_mode}"
            yield step_results
            self.log.info(f"Start to post process, use mode: {postp_mode}")
            
            if postp_mode == "rm":
                step_results["temp_final_audio_path"] = None
            elif postp_mode == "rep":
                step_results["temp_final_audio_path"] = step_results["step1_audio_path"]
                step_results["temp_final_video_path"] = step_results["step1_video_path"]
            elif postp_mode == "neg":
                neg_audio_path, neg_video_path = self.step1.run(video_input, output_dir, prompt, negative_prompt='human voice', duration=duration, seed=seed, is_postp=True)
                step_results["temp_final_audio_path"] = neg_audio_path
                step_results["temp_final_video_path"] = neg_video_path
            else:
                self.log.error(f"Error postp_mode: {postp_mode}")
    
            self.log.info(f"After post-processing, audio is {step_results['temp_final_audio_path']} and video is {step_results['temp_final_video_path']}")
            self.log.info(f"Finish Post-Process successfully.\n")
            step_results['log'] = f"Post-processing completed."
            yield step_results
            
            
        step_results['log'] = "Finish step-by-step v2a."
        yield step_results

