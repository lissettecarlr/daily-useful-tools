import os
import argparse
from openai import OpenAI
from pathlib import Path
from typing import List
from dotenv import load_dotenv


load_dotenv()

def get_all_files(directory: str) -> tuple[dict, dict]:
    """获取目录下的所有文件，返回视频文件和字幕文件的字典"""
    video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.rmvb', '.flv', '.wmv', '.webm'}
    subtitle_extensions = {'.srt', '.ass', '.ssa'}
    
    video_files = {}
    subtitle_files = {}
    
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            full_path = os.path.join(root, filename)
            if ext in video_extensions:
                video_files[filename] = full_path
            elif ext in subtitle_extensions:
                subtitle_files[filename] = full_path
                
    return video_files, subtitle_files

def generate_new_filename(video_name_list: List[str], subtitle_name_list: List[str]) -> str:
    """
    使用大模型进行重命名设计
    """
    system_prompt = """
        你是一个番剧重命名助手，对番剧是视频文件和字幕文件进行重命名，返回json格式

        重命名规则：
        1. 最终输出格式：番剧名称 - 季数和集数 - 额外信息.后缀
        2. 番剧名称：从文件原始名称中提取，如果包含中英两种名称，则英文在前中文在后。
        3. 季数和集数：采用S01E01的格式，从文件原始名称中提取，如果没有说明是第几季则默认是SO1。如果是是PV或者发现是不归属于正剧的视频则使用S00
        4. 额外信息：如果文件原始名称中包含的视频信息如1080p、BDRip则添加，其他信息则忽略
        5. 字幕文件必须和视频文件名称相同

        示例1：
        输入名称：[DBD-Raws][Re Zero kara Hajimeru Isekai Seikatsu Memory Snow][PV][01][1080P][BDRip][HEVC-10bit][FLAC].mkv
        输出名称：Re Zero kara Hajimeru Isekai Seikatsu Memory Snow - S00E01 - 1080P.BDRip.mkv

        示例2:
        输入名称：[Re：从零开始的异世界的生活_Re Zero kara Hajimeru Isekai Seikatsu][59][3rd - 09][WEB-DL_1080P_x264_AAC][简日双语].mp4(301MB)
        输出名称：Re Zero kara Hajimeru Isekai Seikatsu.从零开始的异世界的生活 - S03E09 - 1080P.WEB

        输出json格式：
        [
          {"文件名":"","重命名":""}
        ]
        禁止使用```json```包裹代码
    """

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )

    user_prompt = f"""
    视频文件列表: {video_name_list}
    字幕文件列表: {subtitle_name_list}
    """
    
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    )
    
    return completion.choices[0].message.content.strip()

def rename_files(directory: str):
    """主函数：重命名文件"""
    video_files, subtitle_files = get_all_files(directory)
    if not video_files and not subtitle_files:
        print("未找到文件")
        return
    
    print(f"找到 {len(video_files)} 个视频文件和 {len(subtitle_files)} 个字幕文件")
    
    video_filenames = list(video_files.keys())
    subtitle_filenames = list(subtitle_files.keys())

    new_names_json = generate_new_filename(video_filenames, subtitle_filenames)
    try:
        import json
        rename_plan = []
        rename_info_list = json.loads(new_names_json)
        
        # 创建重命名计划
        for info in rename_info_list:
            old_name = info['文件名']
            new_name = info['重命名']
            
            # 检查是视频还是字幕文件
            if old_name in video_files:
                rename_plan.append({
                    'type': '视频',
                    'old_path': video_files[old_name],
                    'new_name': new_name
                })
            elif old_name in subtitle_files:
                rename_plan.append({
                    'type': '字幕',
                    'old_path': subtitle_files[old_name],
                    'new_name': new_name
                })
                
        # 展示重命名计划
        print("\n重命名计划:")
        for item in rename_plan:
            print(f"\n{item['type']}文件:")
            print(f"{item['old_path']}")
            print(f"-> {os.path.join(os.path.dirname(item['old_path']), item['new_name'])}")
        
        # 一次性确认
        confirm = input("\n是否确认执行重命名？(y/n): ").lower()
        if confirm == 'y':
            for item in rename_plan:
                try:
                    new_file_path = os.path.join(
                        os.path.dirname(item['old_path']),
                        item['new_name']
                    )
                    os.rename(item['old_path'], new_file_path)
                    print(f"重命名成功: {item['old_path']} -> {new_file_path}")
                except Exception as e:
                    print(f"重命名失败 {item['old_path']}: {str(e)}")
        else:
            print("已取消重命名操作")
    except Exception as e:
        print(f"解析AI返回结果失败: {str(e)}")
        return

def main():
    parser = argparse.ArgumentParser(description='番剧重命名工具')
    parser.add_argument('directory', help='番剧目录路径')

    args = parser.parse_args()
    
    if not os.path.isdir(args.directory):
        print(f"错误: {args.directory} 不是一个有效的目录")
        return
    
    rename_files(args.directory)

if __name__ == "__main__":
    main() 
