# coding = utf-8

import sys
import os

# 获取 'third_party/MMAudio' 的绝对路径
project_root = os.path.dirname(os.path.abspath(__file__))
mmaudio_path = os.path.join(project_root, 'third_party', 'MMAudio')
# foleyc_path = os.path.join(project_root, 'third_party', 'FoleyCrafter')
# musicsep_path = os.path.join(project_root, 'third_party', 'MusicSoundSeparationTraining')
# vllm2_path = os.path.join(project_root, 'third_party', 'VideoLLaMA2')

# 将 'third_party/MMAudio' 目录添加到 sys.path
sys.path.append(mmaudio_path)

import argparse

from pipeline.pipeline import Pipeline
from third_party.MMAudio.mmaudio.eval_utils import setup_eval_logging
import os
from moviepy.editor import AudioFileClip, VideoFileClip



def parse_args():
    parser = argparse.ArgumentParser(description="Arguments for the model configuration")
    parser.add_argument('--mode', type=str, 
                        choices=['s3', 's4'], 
                        default='s4', 
                        help="until step3 or step4")
    parser.add_argument('--step1_mode', type=str, 
                        choices=['mmaudio_small_16k', 'mmaudio_small_44k', 'mmaudio_medium_44k', 'mmaudio_large_44k', 'mmaudio_large_44k_v2' 'foleycrafter'], 
                        default='mmaudio_large_44k_v2', 
                        help='v2a method')
    parser.add_argument('--step2_mode', type=str, choices=['qa', 'cot'], 
                        default='cot', 
                        help="judge voice-over method")
    parser.add_argument('--step3_mode', type=str, 
                        choices=['bs_roformer'], 
                        default='bs_roformer', 
                        help="remove voice-over method")
    parser.add_argument('--postp_mode', type=str, 
                        choices=['rm', 'rep', 'neg'], 
                        default='rep', 
                        help="post-process method")
    parser.add_argument('--step0_model_dir', type=str, 
                        default='pretrained/mllm/VideoLLaMA2.1-7B-AV-CoT', 
                        help="step0 model dir")
    parser.add_argument('--step2_model_dir', type=str, 
                        default='pretrained/mllm/VideoLLaMA2.1-7B-AV-CoT', 
                        help="judge voice-over model dir")
    

    parser.add_argument('--gen_video', type=str, 
                        default='true', 
                        help="Whether to generate video, true means yes")
    
    parser.add_argument('--prompt', type=str, 
                        default='', 
                        help="prompt for v2a")
    
    parser.add_argument('--negative_prompt', type=str, 
                        default='', 
                        help="negative_prompt for v2a")
    
    parser.add_argument('--duration', type=float, 
                        default=10, 
                        help="generate duration")
    
    parser.add_argument('--output_dir', type=str, 
                        default='outputs', 
                        help="output dir")
    
    parser.add_argument('--video_input', type=str, 
                        default='ZxiXftx2EMg_000477.mp4', 
                        # required=True,
                        help="video input path")
    
    return parser.parse_args()

# 示例使用
if __name__ == '__main__':
    args = parse_args()
    setup_eval_logging()

    pipeline = Pipeline(
        step0_model_dir=args.step0_model_dir, 
        step1_mode=args.step1_mode, 
        step2_model_dir=args.step2_model_dir,
        step2_mode=args.step2_mode,
        step3_mode=args.step3_mode,
    )

    # video_input = 'input_video.mp4'
    # output_dir = "outputs"
    os.makedirs(args.output_dir, exist_ok=True)
    step_results = pipeline.run(video_input=args.video_input, 
                                output_dir=args.output_dir,
                                mode=args.mode,
                                postp_mode=args.postp_mode,
                                prompt=args.prompt,
                                negative_prompt=args.negative_prompt,
                                duration=args.duration)
    
    final_audio_path = step_results["final_audio_path"]
    final_video_path = step_results["final_video_path"]

    if args.gen_video:
        if final_audio_path is not None and final_video_path is None:
            save_video_path = final_audio_path.replace(".wav", ",mp4")
            audio = AudioFileClip(final_audio_path)
            video = VideoFileClip(args.video_input)
            audio = audio.subclip(0, args.duration)
            video.audio = audio
            video = video.subclip(0, args.duration)
            video.write_videofile(save_video_path)
            step_results["final_video_path"] = save_video_path

    print("step_results: ", step_results)
    print(f"final_audio_path: {step_results['final_audio_path']}")
    print(f"final_video_path: {step_results['final_video_path']}")
