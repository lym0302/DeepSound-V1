# coding=utf-8
# V2A
import logging


class Step1:
    def __init__(self, step1_mode):
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.INFO)

        if step1_mode.startswith('mmaudio'):
            from v2a_models.v2a_mmaudio import V2A_MMAudio
            variant = step1_mode.replace("mmaudio_", "")
            self.v2a_model = V2A_MMAudio(variant)
        elif step1_mode == "foleycrafter":
            from v2a_models.v2a_foleycrafter import V2A_FoleyCrafter
            self.v2a_model = V2A_FoleyCrafter()
        else:
            self.log.error(f"Error step1_mode: {step1_mode}")



    def run(self, video_path, output_dir, prompt='', negative_prompt='', duration=10, is_postp=False, ):
        # self.log.info("Step1: Generate audio from video.")
        step1_audio_path, step1_video_path = self.v2a_model.generate_audio(
            video_path=video_path,
            output_dir=output_dir,
            prompt=prompt,
            negative_prompt=negative_prompt,
            duration=duration,
            is_postp=is_postp)
        
        self.log.info(f"The audio generated by Step1 is in {step1_audio_path}, and the video is in {step1_video_path}")
        self.log.info("Finish Step1 successfully.\n")
        return step1_audio_path, step1_video_path
