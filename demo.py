"""
原创解说剪辑服务 - 完整AI流程实现
视频画面分析 → 文案生成 → 智能配音 → 三同步
"""
import logging
import os
import json
import time
import uuid
import numpy as np
import hashlib
import cv2
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path
import time
from backend.services import TaskService

from backend.config.paths import PROJECT_ROOT, AUDIO_DIR, TEMP_DIR, OUTPUTS_DIR
from backend.engine import VideoProcessor
from backend.engine.video_composer import VideoComposer
from backend.engine.subtitle_generator import SubtitleGenerator

# Flask相关导入
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from werkzeug.utils import secure_filename


# 创建Flask应用
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'jjyb_ai_secret_key_2025'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024
# 启用CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})
# 创建SocketIO实例
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=60, ping_interval=25)

import dill

def dill_read(name):
    with open(name, 'rb') as f:
        content = dill.load(f)
        return content

def dill_write(name, content):
    with open(name, 'wb') as f:
        dill.dump(content, f)


class CommentaryServiceEnhanced:
    def __init__(self):
        from database import DatabaseManager
        self.db_manager = DatabaseManager()
        from backend.config.ai_config import get_config_manager
        self.ai_config = get_config_manager()
        from backend.engine.vision_analyzer import get_vision_analyzer
        self.vision_analyzer = get_vision_analyzer()
        from backend.engine.multi_model_adapter import get_multi_model_manager
        self.multi_model = get_multi_model_manager()
        from backend.engine.script_generator import get_script_generator
        self.script_generator = get_script_generator()
        from backend.engine.tts_engine import get_tts_generator
        self.tts_engine = get_tts_generator()
        from backend.engine.sync_engine import get_sync_engine
        self.sync_engine = get_sync_engine()
        print('======CommentaryServiceEnhanced init======')
        # print(self.vision_analyzer, self.multi_model, self.ai_config.vision_config)

    def create_project(self, data: Dict) -> Dict:
        """创建原创解说项目"""
        try:
            print('🎬 创建原创解说项目...')
            project = self.db_manager.create_project(
                name=data.get('name', '原创解说项目'),
                project_type='commentary',
                description='AI原创解说剪辑',
                template='commentary'
            )
            project_id = project['id']
            # print(self.db_manager.get_all_projects())
            # 保存配置
            config = {
                'video_path': data.get('video_path', ''),
                'script': data.get('script', ''),
                'voice': data.get('voice', 'zh-CN-XiaoxiaoNeural'),
                # 默认使用本地 pyttsx3，避免在无网络环境下频繁触发云TTS失败
                'tts_engine': data.get('tts_engine') or 'pyttsx3',
                'auto_subtitle': data.get('auto_subtitle', True),  # 自动字幕
                'auto_bgm': data.get('auto_bgm', True),            # 自动BGM
                'style': data.get('style', 'professional'),        # 文稿风格
                # 字幕样式相关配置：允许前端覆盖默认大号样式和位置/字号
                'subtitle_style': data.get('subtitle_style') or 'default',       # 字幕样式
                'subtitle_position': data.get('subtitle_position') or 'bottom',  # 字幕位置
                'subtitle_font_size': data.get('subtitle_font_size') or None,    # 字体大小
                # 高级字幕样式：字体 / 颜色 / 描边 / 背景
                'subtitle_font': data.get('subtitle_font') or None,
                'subtitle_color': data.get('subtitle_color')  or None,
                'subtitle_bg_color': data.get('subtitle_bg_color') or None,
                'subtitle_stroke_color': data.get('subtitle_stroke_color') or None,
                'subtitle_stroke_width': data.get('subtitle_stroke_width') or None,
            }
            # 保存音量控制配置
            voice_volume = data.get('voice_volume') or 100  # 配音音量
            bgm_volume = data.get('bgm_volume') or 30      # BGM音量
            original_audio_volume = data.get('original_audio_volume') or 20  # 原始音频音量
            if voice_volume is not None:
                config['voice_volume'] = float(voice_volume)
            if bgm_volume is not None:
                config['bgm_volume'] = float(bgm_volume)
            if original_audio_volume is not None:
                config['original_audio_volume'] = float(original_audio_volume)

            self.db_manager.update_project(project_id, {'config': config})
            print(f'✅ 项目创建成功: {project_id}')
            return {
                'code': 0,
                'msg': '项目创建成功',
                'data': {
                    'project_id': project_id,
                    'project': project,
                    'config': config
                }
            }
        except Exception as ex:
            print(f'❌ 创建项目失败: {ex}')
            return {'code': 1, 'msg': f'创建失败: {str(ex)}', 'data': None}

    def process_video(self, project_id: str, video_path: str, config: Dict) -> Dict:
        # 完整处理流程：分析 → 生成 → 配音 → 同步
        # 'id': '41e83ca4-873f-4071-a588-673c396d610e'
        # 'project_id': '08951a10-2cbf-4178-87d3-b0786a5ca368'
        try:
            print(f'🚀 开始处理项目: {project_id}')
            def get_task_id(project_id, video_path, config):
                # 创建任务（写入数据库）
                task_id = str(uuid.uuid4())
                self.db_manager.create_task(
                    task_id=task_id,
                    task_type='commentary_process',
                    project_id=project_id,
                    input_data={'video_path': video_path, 'config': config}
                )
                self.db_manager.update_task_status(task_id, 'running')
                print(self.db_manager.get_task(task_id))
                return task_id
            # task_id = get_task_id(project_id, video_path, config)
            task_id = '41e83ca4-873f-4071-a588-673c396d610e'

            # 步骤1: 分析视频画面
            def get_analyze_video(video_path, config):
                print('=====正在分析视频画面=====')
                vision_results = self._analyze_video(video_path, config)
                if not vision_results:
                    raise Exception('视频分析失败')
                print('=====视频分析缓存完成=====')
                return vision_results
            vision_results = get_analyze_video(video_path, config)
            exit()
            # 步骤2: AI生成文案
            def get_generate_script(vision_results, config, task_id):
                print('=====正在生成解说文案=====')
                script = self._generate_script(vision_results, config, task_id)
                if not script:
                    raise Exception('文案生成失败')
                print('=====文案生成缓存完成=====')
                print(script)
                return script
            script = get_generate_script(vision_results, config, task_id)
            # script = {'title': '狂飙工地风云：一跪定乾坤', 'opening': '表面看他风光无限，可真相却让人意外。', 'segments': [{'scene_id': 1, 'start_time': 0.0, 'end_time': 25.0,'text': '书婷披着棕色大衣，快步穿过蓝色围挡。一声老爹喊得清脆，唤醒了旧日情分。启强紧跟在侧后方，黄帽压住沉稳眉眼。看似寻常视察现场，实则暗流早已涌动。图纸紧紧攥在手里，目光扫过钢筋水泥。', 'emotion': 'neutral', 'emphasis': ['棕色大衣', '暗流涌动']}, {'scene_id': 2, 'start_time': 25.0, 'end_time': 55.0, 'text': '启盛笑着递上文件，兄妹紧紧相拥片刻。温情不过转眼即逝，利益网已悄然铺开。老默低头核对数据，小龙静立一旁等候。镜头缓缓向前推移，书婷轻揽泰叔肩膀。她侧身低声做引荐，那句就是高启强。', 'emotion': 'sad', 'emphasis': ['利益网', '侧身引荐']}, {'scene_id': 3, 'start_time': 55.0, 'end_time': 85.0, 'text': '泰叔目光微微下沉，并未立刻伸手回应。启强收起面上笑意，双手交叠立于原地。上位者的无声审视，让空气瞬间变凝重。安全帽遮住半张脸，却遮不住岁月痕迹。哪曾想刚才的从容，转眼化作极致卑微。他双膝重重砸向地，额头紧贴冰冷水泥。', 'emotion': 'tense', 'emphasis': ['目光微沉', '双膝砸地']}, {'scene_id': 4, 'start_time': 85.0, 'end_time': 115.0, 'text': '泰叔双手深深插兜，居高临下冷眼旁观。书婷侧立沉默不语，眼底藏着复杂权衡。权力面前体面尽失，从来都是昂贵代价。老人眉头紧紧锁起，字字句句皆是敲打。启强低头安静聆听，不敢有半分去反驳。沉默是无声的对抗，也是蛰伏的筹码。', 'emotion': 'sad', 'emphasis': ['居高临下', '无声对抗']}, {'scene_id': 5, 'start_time': 115.0, 'end_time': 140.0, 'text': '身后众人全部屏息，只听见风声过工地。灰色西装沾染尘土，却掩盖不住锋芒。江湖规矩从来如此，只看实力不看脸面。训话终于缓缓结束，泰叔转身不再多言。启强慢慢站起身来，眼底野心重新燃起。', 'emotion': 'neutral', 'emphasis': ['蛰伏筹码', '野心燃起']}, {'scene_id': 6, 'start_time': 140.0, 'end_time': 153.0, 'text': '书婷递来一个眼神，默契尽在不言中。工地依旧喧嚣嘈杂，命运齿轮悄然转动。所谓上位艰难之路，不过是一场修行。', 'emotion': 'reflective', 'emphasis': ['命运齿轮', '漫长修行']}], 'closing': '繁华落尽皆是迷局，步步惊心方知进退。', 'total_duration': 153.0, 'original_chars': 534, 'optimized_chars': 534, 'char_limit': 535}
            exit()
            # 步骤3: 智能配音
            def get_generate_voiceover(script, config, task_id):
                print('=====正在生成配音=====')
                audio_path = self._generate_voiceover(script, config, task_id)
                if not audio_path:
                    raise Exception('配音生成失败')
                print('=====配音生成完成=====')
                print(audio_path)
                return audio_path
            # audio_path = get_generate_voiceover(script, config, task_id)
            audio_path = "output/commentary_audio_1779779773_0cb6c5.mp3"
            # exit()
            # 步骤4: 三同步处理
            print('=====开始执行三同步处理=====')
            # sync_results = self._sync_all(video_path, audio_path, script, vision_results, task_id)
            sync_results = {'audio_video_sync': {'tempo': 161.4990234375, 'beats': [0.13931972789115646, 0.5340589569160997, 0.905578231292517, 1.2770975056689342, 1.6486167800453515, 1.9969160997732427, 2.36843537414966, 2.693514739229025, 3.01859410430839, 3.3436734693877552, 3.7151927437641725, 4.1099319727891155, 4.481451247165533, 4.85297052154195, 5.224489795918367, 5.596009070294785, 5.990748299319728, 6.339047619047619, 6.710566893424036, 7.058866213151927, 7.4071655328798185, 7.778684807256236, 8.150204081632653, 8.498503401360544, 8.846802721088435, 9.195102040816327, 9.543401360544218, 9.891700680272109, 10.24, 10.611519274376418, 10.95981859410431, 11.3081179138322, 11.633197278911565, 11.981496598639456, 12.329795918367347, 12.701315192743763, 13.072834467120181, 13.421133786848072, 13.769433106575963, 14.094512471655328, 14.466031746031746, 14.814331065759637, 15.162630385487528, 15.487709750566893, 15.836009070294784, 16.207528344671204, 16.579047619047618, 16.950566893424035, 17.322086167800453, 17.670385487528346, 18.04190476190476, 18.390204081632653, 18.738503401360543, 19.06358276643991, 19.481541950113378, 19.87628117913832, 20.271020408163267, 20.64253968253968, 21.0140589569161, 21.385578231292516, 21.757097505668934, 22.19827664399093, 22.639455782312925, 23.057414965986396, 23.45215419501134, 23.870113378684806, 24.241632653061224, 24.589931972789117, 24.938231292517006, 25.356190476190477, 25.704489795918366, 26.09922902494331, 26.470748299319727, 26.842267573696144, 27.213786848072562, 27.631746031746033, 28.0497052154195, 28.421224489795918, 28.81596371882086, 29.18748299319728, 29.512562358276643, 29.837641723356008, 30.209160997732425, 30.580680272108843, 30.95219954648526, 31.30049886621315, 31.648798185941043, 31.997097505668933, 32.36861678004535, 32.74013605442177, 33.08843537414966, 33.41351473922902, 33.761814058956915, 34.13333333333333, 34.528072562358275, 34.89959183673469, 35.27111111111111, 35.64263038548753, 36.014149659863946, 36.385668934240364, 36.75718820861678, 37.1287074829932, 37.50022675736962, 37.871746031746035, 38.196825396825396, 38.568344671201814, 38.93986394557823, 39.288163265306125, 39.63646258503401, 39.9847619047619, 40.30984126984127, 40.63492063492063, 41.00643990929705, 41.35473922902494, 41.749478458049886, 42.14421768707483, 42.515736961451246, 42.887256235827664, 43.25877551020408, 43.607074829931975, 44.00181405895692, 44.373333333333335, 44.74485260770975, 45.09315192743764, 45.44145124716553, 45.81297052154195, 46.16126984126984, 46.53278911564626, 46.9275283446712, 47.29904761904762, 47.67056689342404, 48.042086167800456, 48.41360544217687, 48.78512471655329, 49.1566439909297, 49.504943310657595, 49.87646258503401, 50.224761904761905, 50.59628117913832, 50.96780045351474, 51.33931972789116, 51.710839002267576, 52.05913832199546, 52.407437641723355, 52.75573696145125, 53.10403628117914, 53.4291156462585, 53.80063492063492, 54.14893424036281, 54.52045351473923, 54.868752834467124, 55.21705215419501, 55.54213151927438, 55.913650793650795, 56.28517006802721, 56.610249433106574, 56.95854875283447, 57.283628117913835, 57.608707482993196, 57.95700680272109, 58.30530612244898, 58.700045351473925, 59.09478458049887, 59.48952380952381, 59.90748299319728, 60.32544217687075, 60.69696145124716, 61.09170068027211, 61.46321995464853, 61.83473922902494, 62.20625850340136, 62.577777777777776, 62.94929705215419, 63.32081632653061, 63.69233560090703, 64.06385487528345, 64.41215419501134, 64.78367346938775, 65.15519274376418, 65.52671201814059, 65.87501133786849, 66.17687074829932, 66.52517006802721, 66.87346938775511, 67.19854875283447, 67.61650793650794, 68.01124716553288, 68.40598639455783, 68.77750566893424, 69.12580498866213, 69.52054421768707, 69.89206349206349, 70.24036281179139, 70.58866213151927, 70.93696145124717, 71.28526077097506, 71.65678004535147, 72.02829931972789, 72.3998185941043, 72.79455782312925, 73.18929705215419, 73.63047619047619, 73.97877551020409, 74.37351473922902, 74.81469387755102, 75.2326530612245, 75.60417233560091, 75.97569160997732, 76.34721088435374, 76.71873015873015, 77.09024943310658, 77.46176870748299, 77.87972789115646, 78.27446712018141, 78.66920634920635, 79.04072562358277, 79.41224489795918, 79.7837641723356, 80.17850340136054, 80.5732426303855, 80.96798185941043, 81.33950113378685, 81.75746031746031, 82.12897959183674, 82.4540589569161, 82.82557823129251, 83.19709750566894, 83.54539682539682, 83.94013605442177, 84.28843537414966, 84.63673469387756, 84.98503401360544, 85.33333333333333, 85.6584126984127, 85.98349206349206, 86.35501133786848, 86.7265306122449, 87.09804988662131, 87.46956916099774, 87.86430839002267, 88.2358276643991, 88.58412698412698, 88.9556462585034, 89.32716553287982, 89.69868480725624, 90.07020408163265, 90.4649433106576, 90.83646258503401, 91.20798185941042, 91.57950113378685, 91.90458049886621, 92.25287981859411, 92.601179138322, 92.9726984126984, 93.3209977324263, 93.66929705215419, 94.01759637188209, 94.3891156462585, 94.76063492063491, 95.13215419501134, 95.50367346938775, 95.85197278911565, 96.22349206349206, 96.59501133786848, 96.94331065759637, 97.36126984126984, 97.73278911564626, 98.10430839002268, 98.47582766439909, 98.84734693877552, 99.1956462585034, 99.54394557823129, 99.89224489795919, 100.21732426303855, 100.56562358276643, 100.91392290249433, 101.26222222222222, 101.63374149659865, 101.958820861678, 102.33034013605442, 102.67863945578232, 103.0269387755102, 103.39845804988663, 103.76997732426304, 104.14149659863945, 104.51301587301587, 104.86131519274376, 105.20961451247166, 105.58113378684807, 105.92943310657597, 106.30095238095238, 106.67247165532879, 107.04399092970522, 107.43873015873015, 107.78702947845805, 108.13532879818594, 108.48362811791384, 108.8087074829932, 109.22666666666667, 109.64462585034013, 109.9697052154195, 110.34122448979592, 110.71274376417233, 111.06104308390023, 111.45578231292517, 111.85052154195012, 112.22204081632653, 112.59356009070295, 112.96507936507936, 113.31337868480726, 113.66167800453515, 114.07963718820862, 114.45115646258503, 114.82267573696146, 115.19419501133787, 115.56571428571428, 115.9372335600907, 116.30875283446711, 116.70349206349206, 117.07501133786847, 117.4465306122449, 117.84126984126983, 118.18956916099773, 118.53786848072562, 118.88616780045352, 119.2344671201814, 119.58276643990929, 119.97750566893424, 120.34902494331065, 120.72054421768708, 121.09206349206349, 121.44036281179139, 121.83510204081632, 122.18340136054422, 122.55492063492063, 122.92643990929706, 123.27473922902495, 123.62303854875283, 123.99455782312926, 124.41251700680272, 124.80725623582767, 125.15555555555555, 125.50385487528345, 125.85215419501134, 126.20045351473922, 126.54875283446712, 126.89705215419501, 127.29179138321996, 127.66331065759637, 128.03482993197278, 128.3831292517007, 128.73142857142858, 129.10294784580498, 129.4512471655329, 129.89242630385488], 'aligned_segments': [{'scene_id': 1, 'start_time': 0.0, 'end_time': 25.0, 'text': '书婷披着棕色大衣，快步穿过蓝色围挡。一声老爹喊得清脆，唤醒了旧日情分。启强紧跟在侧后方，黄帽压住沉稳眉眼。看似寻常视察现场，实则暗流早已涌动。图纸紧紧攥在手里，目光扫过钢筋水泥。', 'emotion': 'neutral', 'emphasis': ['棕色大衣', '暗流涌动'], 'original_start': 0.0, 'original_end': 25.0, 'aligned_start': 0.13931972789115646, 'aligned_end': 24.938231292517006, 'start_adjustment': 0.13931972789115646, 'end_adjustment': -0.06176870748299379}, {'scene_id': 2, 'start_time': 25.0, 'end_time': 55.0, 'text': '启盛笑着递上文件，兄妹紧紧相拥片刻。温情不过转眼即逝，利益网已悄然铺开。老默低头核对数据，小龙静立一旁等候。镜头缓缓向前推移，书婷轻揽泰叔肩膀。她侧身低声做引荐，那句就是高启强。', 'emotion': 'sad', 'emphasis': ['利益网', '侧身引荐'], 'original_start': 25.0, 'original_end': 55.0, 'aligned_start': 24.938231292517006, 'aligned_end': 54.868752834467124, 'start_adjustment': -0.06176870748299379, 'end_adjustment': -0.1312471655328764}, {'scene_id': 3, 'start_time': 55.0, 'end_time': 85.0, 'text': '泰叔目光微微下沉，并未立刻伸手回应。启强收起面上笑意，双手交叠立于原地。上位者的无声审视，让空气瞬间变凝重。安全帽遮住半张脸，却遮不住岁月痕迹。哪曾想刚才的从容，转眼化作极致卑微。他双膝重重砸向地，额头紧贴冰冷水泥。', 'emotion': 'tense', 'emphasis': ['目光微沉', '双膝砸地'], 'original_start': 55.0, 'original_end': 85.0, 'aligned_start': 54.868752834467124, 'aligned_end': 84.98503401360544, 'start_adjustment': -0.1312471655328764, 'end_adjustment': -0.014965986394557262}, {'scene_id': 4, 'start_time': 85.0, 'end_time': 115.0, 'text': '泰叔双手深深插兜，居高临下冷眼旁观。书婷侧立沉默不语，眼底藏着复杂权衡。权力面前体面尽失，从来都是昂贵代价。老人眉头紧紧锁起，字字句句皆是敲打。启强低头安静聆听，不敢有半分去反驳。沉默是无声的对抗，也是蛰伏的筹码。', 'emotion': 'sad', 'emphasis': ['居高临下', '无声对抗'], 'original_start': 85.0, 'original_end': 115.0, 'aligned_start': 84.98503401360544, 'aligned_end': 114.82267573696146, 'start_adjustment': -0.014965986394557262, 'end_adjustment': -0.17732426303854254}, {'scene_id': 5, 'start_time': 115.0, 'end_time': 140.0, 'text': '身后众人全部屏息，只听见风声过工地。灰色西装沾染尘土，却掩盖不住锋芒。江湖规矩从来如此，只看实力不看脸面。训话终于缓缓结束，泰叔转身不再多言。启强慢慢站起身来，眼底野心重新燃起。', 'emotion': 'neutral', 'emphasis': ['蛰伏筹码', '野心燃起'], 'original_start': 115.0, 'original_end': 140.0, 'aligned_start': 114.82267573696146, 'aligned_end': 129.89242630385488, 'start_adjustment': -0.17732426303854254, 'end_adjustment': -10.107573696145124}, {'scene_id': 6, 'start_time': 140.0, 'end_time': 153.0, 'text': '书婷递来一个眼神，默契尽在不言中。工地依旧喧嚣嘈杂，命运齿轮悄然转动。所谓上位艰难之路，不过是一场修行。', 'emotion': 'reflective', 'emphasis': ['命运齿轮', '漫长修行'], 'original_start': 140.0, 'original_end': 153.0, 'aligned_start': 129.89242630385488, 'aligned_end': 142.89242630385488, 'start_adjustment': -10.107573696145124, 'end_adjustment': -10.107573696145124}], 'adjustments': [{'segment_id': 1, 'start_adjustment': 0.13931972789115646, 'end_adjustment': -0.06176870748299379}, {'segment_id': 2, 'start_adjustment': -0.06176870748299379, 'end_adjustment': -0.1312471655328764}, {'segment_id': 3, 'start_adjustment': -0.1312471655328764, 'end_adjustment': -0.014965986394557262}, {'segment_id': 4, 'start_adjustment': -0.014965986394557262, 'end_adjustment': -0.17732426303854254}, {'segment_id': 5, 'start_adjustment': -0.17732426303854254, 'end_adjustment': -10.107573696145124}, {'segment_id': 6, 'start_adjustment': -10.107573696145124, 'end_adjustment': -10.107573696145124}]}, 'audio_text_sync': {'word_timings': [{'word': '书婷披着棕色大衣', 'start': 0.0, 'end': 1.25, 'segment_id': 1}, {'word': '，', 'start': 1.25, 'end': 2.5, 'segment_id': 1}, {'word': '快步穿过蓝色围挡', 'start': 2.5, 'end': 3.75, 'segment_id': 1}, {'word': '。', 'start': 3.75, 'end': 5.0, 'segment_id': 1}, {'word': '一声老爹喊得清脆', 'start': 5.0, 'end': 6.25, 'segment_id': 1}, {'word': '，', 'start': 6.25, 'end': 7.5, 'segment_id': 1}, {'word': '唤醒了旧日情分', 'start': 7.5, 'end': 8.75, 'segment_id': 1}, {'word': '。', 'start': 8.75, 'end': 10.0, 'segment_id': 1}, {'word': '启强紧跟在侧后方', 'start': 10.0, 'end': 11.25, 'segment_id': 1}, {'word': '，', 'start': 11.25, 'end': 12.5, 'segment_id': 1}, {'word': '黄帽压住沉稳眉眼', 'start': 12.5, 'end': 13.75, 'segment_id': 1}, {'word': '。', 'start': 13.75, 'end': 15.0, 'segment_id': 1}, {'word': '看似寻常视察现场', 'start': 15.0, 'end': 16.25, 'segment_id': 1}, {'word': '，', 'start': 16.25, 'end': 17.5, 'segment_id': 1}, {'word': '实则暗流早已涌动', 'start': 17.5, 'end': 18.75, 'segment_id': 1}, {'word': '。', 'start': 18.75, 'end': 20.0, 'segment_id': 1}, {'word': '图纸紧紧攥在手里', 'start': 20.0, 'end': 21.25, 'segment_id': 1}, {'word': '，', 'start': 21.25, 'end': 22.5, 'segment_id': 1}, {'word': '目光扫过钢筋水泥', 'start': 22.5, 'end': 23.75, 'segment_id': 1}, {'word': '。', 'start': 23.75, 'end': 25.0, 'segment_id': 1}, {'word': '启盛笑着递上文件', 'start': 25.0, 'end': 26.5, 'segment_id': 2}, {'word': '，', 'start': 26.5, 'end': 28.0, 'segment_id': 2}, {'word': '兄妹紧紧相拥片刻', 'start': 28.0, 'end': 29.5, 'segment_id': 2}, {'word': '。', 'start': 29.5, 'end': 31.0, 'segment_id': 2}, {'word': '温情不过转眼即逝', 'start': 31.0, 'end': 32.5, 'segment_id': 2}, {'word': '，', 'start': 32.5, 'end': 34.0, 'segment_id': 2}, {'word': '利益网已悄然铺开', 'start': 34.0, 'end': 35.5, 'segment_id': 2}, {'word': '。', 'start': 35.5, 'end': 37.0, 'segment_id': 2}, {'word': '老默低头核对数据', 'start': 37.0, 'end': 38.5, 'segment_id': 2}, {'word': '，', 'start': 38.5, 'end': 40.0, 'segment_id': 2}, {'word': '小龙静立一旁等候', 'start': 40.0, 'end': 41.5, 'segment_id': 2}, {'word': '。', 'start': 41.5, 'end': 43.0, 'segment_id': 2}, {'word': '镜头缓缓向前推移', 'start': 43.0, 'end': 44.5, 'segment_id': 2}, {'word': '，', 'start': 44.5, 'end': 46.0, 'segment_id': 2}, {'word': '书婷轻揽泰叔肩膀', 'start': 46.0, 'end': 47.5, 'segment_id': 2}, {'word': '。', 'start': 47.5, 'end': 49.0, 'segment_id': 2}, {'word': '她侧身低声做引荐', 'start': 49.0, 'end': 50.5, 'segment_id': 2}, {'word': '，', 'start': 50.5, 'end': 52.0, 'segment_id': 2}, {'word': '那句就是高启强', 'start': 52.0, 'end': 53.5, 'segment_id': 2}, {'word': '。', 'start': 53.5, 'end': 55.0, 'segment_id': 2}, {'word': '泰叔目光微微下沉', 'start': 55.0, 'end': 56.25, 'segment_id': 3}, {'word': '，', 'start': 56.25, 'end': 57.5, 'segment_id': 3}, {'word': '并未立刻伸手回应', 'start': 57.5, 'end': 58.75, 'segment_id': 3}, {'word': '。', 'start': 58.75, 'end': 60.0, 'segment_id': 3}, {'word': '启强收起面上笑意', 'start': 60.0, 'end': 61.25, 'segment_id': 3}, {'word': '，', 'start': 61.25, 'end': 62.5, 'segment_id': 3}, {'word': '双手交叠立于原地', 'start': 62.5, 'end': 63.75, 'segment_id': 3}, {'word': '。', 'start': 63.75, 'end': 65.0, 'segment_id': 3}, {'word': '上位者的无声审视', 'start': 65.0, 'end': 66.25, 'segment_id': 3}, {'word': '，', 'start': 66.25, 'end': 67.5, 'segment_id': 3}, {'word': '让空气瞬间变凝重', 'start': 67.5, 'end': 68.75, 'segment_id': 3}, {'word': '。', 'start': 68.75, 'end': 70.0, 'segment_id': 3}, {'word': '安全帽遮住半张脸', 'start': 70.0, 'end': 71.25, 'segment_id': 3}, {'word': '，', 'start': 71.25, 'end': 72.5, 'segment_id': 3}, {'word': '却遮不住岁月痕迹', 'start': 72.5, 'end': 73.75, 'segment_id': 3}, {'word': '。', 'start': 73.75, 'end': 75.0, 'segment_id': 3}, {'word': '哪曾想刚才的从容', 'start': 75.0, 'end': 76.25, 'segment_id': 3}, {'word': '，', 'start': 76.25, 'end': 77.5, 'segment_id': 3}, {'word': '转眼化作极致卑微', 'start': 77.5, 'end': 78.75, 'segment_id': 3}, {'word': '。', 'start': 78.75, 'end': 80.0, 'segment_id': 3}, {'word': '他双膝重重砸向地', 'start': 80.0, 'end': 81.25, 'segment_id': 3}, {'word': '，', 'start': 81.25, 'end': 82.5, 'segment_id': 3}, {'word': '额头紧贴冰冷水泥', 'start': 82.5, 'end': 83.75, 'segment_id': 3}, {'word': '。', 'start': 83.75, 'end': 85.0, 'segment_id': 3}, {'word': '泰叔双手深深插兜', 'start': 85.0, 'end': 86.25, 'segment_id': 4}, {'word': '，', 'start': 86.25, 'end': 87.5, 'segment_id': 4}, {'word': '居高临下冷眼旁观', 'start': 87.5, 'end': 88.75, 'segment_id': 4}, {'word': '。', 'start': 88.75, 'end': 90.0, 'segment_id': 4}, {'word': '书婷侧立沉默不语', 'start': 90.0, 'end': 91.25, 'segment_id': 4}, {'word': '，', 'start': 91.25, 'end': 92.5, 'segment_id': 4}, {'word': '眼底藏着复杂权衡', 'start': 92.5, 'end': 93.75, 'segment_id': 4}, {'word': '。', 'start': 93.75, 'end': 95.0, 'segment_id': 4}, {'word': '权力面前体面尽失', 'start': 95.0, 'end': 96.25, 'segment_id': 4}, {'word': '，', 'start': 96.25, 'end': 97.5, 'segment_id': 4}, {'word': '从来都是昂贵代价', 'start': 97.5, 'end': 98.75, 'segment_id': 4}, {'word': '。', 'start': 98.75, 'end': 100.0, 'segment_id': 4}, {'word': '老人眉头紧紧锁起', 'start': 100.0, 'end': 101.25, 'segment_id': 4}, {'word': '，', 'start': 101.25, 'end': 102.5, 'segment_id': 4}, {'word': '字字句句皆是敲打', 'start': 102.5, 'end': 103.75, 'segment_id': 4}, {'word': '。', 'start': 103.75, 'end': 105.0, 'segment_id': 4}, {'word': '启强低头安静聆听', 'start': 105.0, 'end': 106.25, 'segment_id': 4}, {'word': '，', 'start': 106.25, 'end': 107.5, 'segment_id': 4}, {'word': '不敢有半分去反驳', 'start': 107.5, 'end': 108.75, 'segment_id': 4}, {'word': '。', 'start': 108.75, 'end': 110.0, 'segment_id': 4}, {'word': '沉默是无声的对抗', 'start': 110.0, 'end': 111.25, 'segment_id': 4}, {'word': '，', 'start': 111.25, 'end': 112.5, 'segment_id': 4}, {'word': '也是蛰伏的筹码', 'start': 112.5, 'end': 113.75, 'segment_id': 4}, {'word': '。', 'start': 113.75, 'end': 115.0, 'segment_id': 4}, {'word': '身后众人全部屏息', 'start': 115.0, 'end': 116.25, 'segment_id': 5}, {'word': '，', 'start': 116.25, 'end': 117.5, 'segment_id': 5}, {'word': '只听见风声过工地', 'start': 117.5, 'end': 118.75, 'segment_id': 5}, {'word': '。', 'start': 118.75, 'end': 120.0, 'segment_id': 5}, {'word': '灰色西装沾染尘土', 'start': 120.0, 'end': 121.25, 'segment_id': 5}, {'word': '，', 'start': 121.25, 'end': 122.5, 'segment_id': 5}, {'word': '却掩盖不住锋芒', 'start': 122.5, 'end': 123.75, 'segment_id': 5}, {'word': '。', 'start': 123.75, 'end': 125.0, 'segment_id': 5}, {'word': '江湖规矩从来如此', 'start': 125.0, 'end': 126.25, 'segment_id': 5}, {'word': '，', 'start': 126.25, 'end': 127.5, 'segment_id': 5}, {'word': '只看实力不看脸面', 'start': 127.5, 'end': 128.75, 'segment_id': 5}, {'word': '。', 'start': 128.75, 'end': 130.0, 'segment_id': 5}, {'word': '训话终于缓缓结束', 'start': 130.0, 'end': 131.25, 'segment_id': 5}, {'word': '，', 'start': 131.25, 'end': 132.5, 'segment_id': 5}, {'word': '泰叔转身不再多言', 'start': 132.5, 'end': 133.75, 'segment_id': 5}, {'word': '。', 'start': 133.75, 'end': 135.0, 'segment_id': 5}, {'word': '启强慢慢站起身来', 'start': 135.0, 'end': 136.25, 'segment_id': 5}, {'word': '，', 'start': 136.25, 'end': 137.5, 'segment_id': 5}, {'word': '眼底野心重新燃起', 'start': 137.5, 'end': 138.75, 'segment_id': 5}, {'word': '。', 'start': 138.75, 'end': 140.0, 'segment_id': 5}, {'word': '书婷递来一个眼神', 'start': 140.0, 'end': 141.08333333333334, 'segment_id': 6}, {'word': '，', 'start': 141.08333333333334, 'end': 142.16666666666666, 'segment_id': 6}, {'word': '默契尽在不言中', 'start': 142.16666666666666, 'end': 143.25, 'segment_id': 6}, {'word': '。', 'start': 143.25, 'end': 144.33333333333334, 'segment_id': 6}, {'word': '工地依旧喧嚣嘈杂', 'start': 144.33333333333334, 'end': 145.41666666666666, 'segment_id': 6}, {'word': '，', 'start': 145.41666666666666, 'end': 146.5, 'segment_id': 6}, {'word': '命运齿轮悄然转动', 'start': 146.5, 'end': 147.58333333333334, 'segment_id': 6}, {'word': '。', 'start': 147.58333333333334, 'end': 148.66666666666666, 'segment_id': 6}, {'word': '所谓上位艰难之路', 'start': 148.66666666666666, 'end': 149.75, 'segment_id': 6}, {'word': '，', 'start': 149.75, 'end': 150.83333333333334, 'segment_id': 6}, {'word': '不过是一场修行', 'start': 150.83333333333334, 'end': 151.91666666666666, 'segment_id': 6}, {'word': '。', 'start': 151.91666666666666, 'end': 153.0, 'segment_id': 6}], 'subtitle_segments': [{'text': '书婷披着棕色大衣，快步穿过蓝色围挡。一声老爹喊得清脆，唤醒了旧日情分。启强紧跟在侧后方，黄帽压住沉稳眉眼。看似寻常视察现场，实则暗流早已涌动。图纸紧紧攥在手里，目光扫过钢筋水泥。', 'start': 0.0, 'end': 25.0, 'duration': 25.0, 'speech_duration': 25.0, 'segment_id': 1}, {'text': '启盛笑着递上文件，兄妹紧紧相拥片刻。温情不过转眼即逝，利益网已悄然铺开。老默低头核对数据，小龙静立一旁等候。镜头缓缓向前推移，书婷轻揽泰叔肩膀。她侧身低声做引荐，那句就是高启强。', 'start': 25.0, 'end': 55.0, 'duration': 30.0, 'speech_duration': 30.0, 'segment_id': 2}, {'text': '泰叔目光微微下沉，并未立刻伸手回应。启强收起面上笑意，双手交叠立于原地。上位者的无声审视，让空气瞬间变凝重。安全帽遮住半张脸，却遮不住岁月痕迹。哪曾想刚才的从容，转眼化作极致卑微。他双膝重重砸向地，额头紧贴冰冷水泥。', 'start': 55.0, 'end': 85.0, 'duration': 30.0, 'speech_duration': 30.0, 'segment_id': 3}, {'text': '泰叔双手深深插兜，居高临下冷眼旁观。书婷侧立沉默不语，眼底藏着复杂权衡。权力面前体面尽失，从来都是昂贵代价。老人眉头紧紧锁起，字字句句皆是敲打。启强低头安静聆听，不敢有半分去反驳。沉默是无声的对抗，也是蛰伏的筹码。', 'start': 85.0, 'end': 115.0, 'duration': 30.0, 'speech_duration': 30.0, 'segment_id': 4}, {'text': '身后众人全部屏息，只听见风声过工地。灰色西装沾染尘土，却掩盖不住锋芒。江湖规矩从来如此，只看实力不看脸面。训话终于缓缓结束，泰叔转身不再多言。启强慢慢站起身来，眼底野心重新燃起。', 'start': 115.0, 'end': 140.0, 'duration': 25.0, 'speech_duration': 25.0, 'segment_id': 5}, {'text': '书婷递来一个眼神，默契尽在不言中。工地依旧喧嚣嘈杂，命运齿轮悄然转动。所谓上位艰难之路，不过是一场修行。', 'start': 140.0, 'end': 153.0, 'duration': 13.0, 'speech_duration': 13.0, 'segment_id': 6}], 'sync_method': 'audio', 'total_words': 120}, 'text_video_sync': {'synced_subtitles': [{'text': '书婷披着棕色大衣，快步穿过蓝色围挡。一声老爹喊得清脆，唤醒了旧日情分。启强紧跟在侧后方，黄帽压住沉稳眉眼。看似寻常视察现场，实则暗流早已涌动。图纸紧紧攥在手里，目光扫过钢筋水泥。', 'start_time': 0.0, 'end_time': 25.0, 'scene_id': 1, 'scene_description': '人物在说话', 'position': {'x': 'center', 'y': 'bottom', 'margin': 20}, 'semantic_score': 0.02127659574468085}, {'text': '启盛笑着递上文件，兄妹紧紧相拥片刻。温情不过转眼即逝，利益网已悄然铺开。老默低头核对数据，小龙静立一旁等候。镜头缓缓向前推移，书婷轻揽泰叔肩膀。她侧身低声做引荐，那句就是高启强。', 'start_time': 25.0, 'end_time': 55.0, 'scene_id': 2, 'scene_description': '人物在说话', 'position': {'x': 'center', 'y': 'bottom', 'margin': 20}, 'semantic_score': 0.0}, {'text': '泰叔目光微微下沉，并未立刻伸手回应。启强收起面上笑意，双手交叠立于原地。上位者的无声审视，让空气瞬间变凝重。安全帽遮住半张脸，却遮不住岁月痕迹。哪曾想刚才的从容，转眼化作极致卑微。他双膝重重砸向地，额头紧贴冰冷水泥。', 'start_time': 55.0, 'end_time': 85.0, 'scene_id': 3, 'scene_description': '人物在说话', 'position': {'x': 'center', 'y': 'bottom', 'margin': 20}, 'semantic_score': 0.0}, {'text': '泰叔双手深深插兜，居高临下冷眼旁观。书婷侧立沉默不语，眼底藏着复杂权衡。权力面前体面尽失，从来都是昂贵代价。老人眉头紧紧锁起，字字句句皆是敲打。启强低头安静聆听，不敢有半分去反驳。沉默是无声的对抗，也是蛰伏的筹码。', 'start_time': 85.0, 'end_time': 115.0, 'scene_id': 4, 'scene_description': '人物在说话', 'position': {'x': 'center', 'y': 'bottom', 'margin': 20}, 'semantic_score': 0.017857142857142856}, {'text': '身后众人全部屏息，只听见风声过工地。灰色西装沾染尘土，却掩盖不住锋芒。江湖规矩从来如此，只看实力不看脸面。训话终于缓缓结束，泰叔转身不再多言。启强慢慢站起身来，眼底野心重新燃起。', 'start_time': 115.0, 'end_time': 140.0, 'scene_id': 5, 'scene_description': '人物在说话', 'position': {'x': 'center', 'y': 'bottom', 'margin': 20}, 'semantic_score': 0.0425531914893617}, {'text': '书婷递来一个眼神，默契尽在不言中。工地依旧喧嚣嘈杂，命运齿轮悄然转动。所谓上位艰难之路，不过是一场修行。', 'start_time': 140.0, 'end_time': 153.0, 'scene_id': 6, 'scene_description': '人物在行走', 'position': {'x': 'center', 'y': 'bottom', 'margin': 20}, 'semantic_score': 0.07017543859649122}], 'semantic_matches': [], 'position_suggestions': [{'segment_id': 1, 'suggested_position': {'x': 'center', 'y': 'bottom', 'margin': 20}, 'reason': '默认底部居中'}, {'segment_id': 2, 'suggested_position': {'x': 'center', 'y': 'bottom', 'margin': 20}, 'reason': '默认底部居中'}, {'segment_id': 3, 'suggested_position': {'x': 'center', 'y': 'bottom', 'margin': 20}, 'reason': '默认底部居中'}, {'segment_id': 4, 'suggested_position': {'x': 'center', 'y': 'bottom', 'margin': 20}, 'reason': '默认底部居中'}, {'segment_id': 5, 'suggested_position': {'x': 'center', 'y': 'bottom', 'margin': 20}, 'reason': '默认底部居中'}, {'segment_id': 6, 'suggested_position': {'x': 'center', 'y': 'bottom', 'margin': 20}, 'reason': '默认底部居中'}], 'average_semantic_score': 0.02531039478127944}, 'sync_quality': 0.30843679826042647}
            # print(sync_results)
            # exit()
            output_path = self._compose_final_video(video_path, audio_path, script, sync_results, config, task_id)
            # 任务完成
            self.db_manager.update_task_status(task_id, 'completed')
            # 保存结果
            result_data = {
                'vision_analysis': vision_results,
                'script': script,
                'audio_path': audio_path,
                'sync_results': sync_results,
                'output_path': output_path
            }
            # 将结果转换为 JSON 安全结构，避免 numpy.ndarray 等对象导致序列化失败
            try:
                safe_result_data = json.loads(
                    json.dumps(result_data, ensure_ascii=False, default=lambda o: None)
                )
            except Exception as ex:
                print(f'⚠ 项目结果JSON序列化失败，将使用精简结果结构: {ex}')
                try:
                    va = result_data.get('vision_analysis') or {}
                except Exception:
                    va = {}
                safe_result_data = {
                    'vision_analysis': {
                        'scenes': va.get('scenes'),
                        'descriptions': va.get('descriptions'),
                        'summary': va.get('summary')
                    },
                    'script': result_data.get('script'),
                    'audio_path': result_data.get('audio_path'),
                    'sync_results': result_data.get('sync_results'),
                    'output_path': result_data.get('output_path')
                }
            # 保存到项目
            self.db_manager.update_project(project_id, {
                'result': safe_result_data,
                'status': 'completed'
            })
            print(f'✅ 项目处理完成: {project_id}')
            return {
                'code': 0,
                'msg': '处理完成',
                'data': {
                    'task_id': task_id,
                    'output_path': output_path,
                    'result': safe_result_data
                }
            }
        except Exception as ex:
            print(f'❌ 处理失败: {ex}')
            try:
                self.db_manager.update_task_status(task_id, 'failed', error_message=str(ex))
            except Exception:
                pass
            return {'code': 1, 'msg': f'处理失败: {str(ex)}', 'data': None}

    def _analyze_video(self, video_path: str, config: Optional[Dict] = {}) -> Optional[Dict]:
        """步骤1: 视频画面分析"""
        try:
            if not self.vision_analyzer:
                raise Exception('视觉分析引擎不可用')
            # ========= 基于文件签名的视频分析缓存 =========
            try:
                # 使用 绝对路径 + 文件大小 + 修改时间 构建稳定签名
                video_abs = os.path.abspath(video_path)
                stat = os.stat(video_abs)
                sig_src = f"{video_abs}|{stat.st_size}|{int(stat.st_mtime)}"
                cache_key = hashlib.md5(sig_src.encode('utf-8')).hexdigest()
                analysis_dir = TEMP_DIR / 'analysis'
                analysis_dir.mkdir(parents=True, exist_ok=True)
                cache_file = analysis_dir / f'frame_analysis_{cache_key}.json'
            except Exception as ex:
                print(f'⚠ 计算视频签名失败，将不使用缓存: {ex}')
                cache_file = None
            print(video_abs)
            print(cache_file)

            # 1. 优先尝试复用缓存结果
            if cache_file and cache_file.exists():
                print('============复用视频分析缓存============')
                try:
                    with cache_file.open('r', encoding='utf-8') as f:
                        cached = json.load(f)
                    if isinstance(cached, dict) and cached.get('scenes') is not None:
                        print(f'📂 复用视频分析缓存: {cache_file}')
                        return cached
                except Exception as ex:
                    print(f'⚠ 读取视频分析缓存失败，将重新分析: {ex}')

            # 2. 使用视觉分析引擎
            print('============开始视频画面分析============')
            results = self.vision_analyzer.analyze_video(video_path)

            # 3. 如果配置了多模型，使用多模型增强描述
            keyframes = (results or {}).get('keyframes') or []
            descriptions = (results or {}).get('descriptions') or []
            print('============使用多模型增强画面描述============')
            if self.multi_model and keyframes and descriptions:
                analysis_dir = TEMP_DIR / 'analysis'
                try:
                    analysis_dir.mkdir(parents=True, exist_ok=True)
                except Exception:
                    analysis_dir = TEMP_DIR
                for i, desc in enumerate(descriptions):
                    if i >= len(keyframes):
                        break
                    frame_info = keyframes[i] or {}
                    frame = frame_info.get('image')
                    img_path: Optional[Path] = None
                    # 1）优先使用内存中的图像帧写入临时文件
                    if frame is not None:
                        try:
                            ts = frame_info.get('timestamp') or i
                            img_path = analysis_dir / f'mm_keyframe_{int(ts)}_{i}.jpg'
                            try:
                                # frame 为 numpy.ndarray 时直接写入，cv2.imwrite 返回 bool
                                save_ok = bool(cv2.imwrite(str(img_path), frame))
                            except Exception:
                                save_ok = False
                            if (not save_ok) or (not img_path.exists()):
                                print(f'⚠ 关键帧图片保存失败，跳过多模型分析: index={i}, path={img_path}')
                                img_path = None
                        except Exception as ex:
                            print(f'⚠ 关键帧图片写入异常，跳过该帧多模型分析: index={i}, err={ex}')
                            img_path = None
                    # 2）如果帧数据为空，尝试使用帧信息里已有的图片路径
                    if img_path is None:
                        try:
                            candidate = frame_info.get('image_path') or frame_info.get('path') or frame
                            if isinstance(candidate, str) and os.path.exists(candidate):
                                img_path = Path(candidate)
                        except Exception:
                            img_path = None
                    # 3）最终仍没有可用图片文件，则跳过该帧的多模型分析，避免向通义传递不存在的路径
                    if img_path is None or not img_path.exists():
                        continue
                    try:
                        prompt = (
                                "请详细、准确地描述这个画面的内容。\n"
                                "重要要求：\n"
                                "1. 如果画面中有动物，必须准确识别其种类（如老虎、狮子、斑马等），不得臆测或替换\n"
                                "2. 如果看不清楚或不确定，直接说'不清楚'或'模糊'，不要乱猜\n"
                                "3. 描述画面中的场景、主体、动作、情绪和氛围\n"
                                "4. 用简洁准确的中文，不超过100字"
                            )
                        prompt = (
                                "请详细精准描述《狂飙》相关影视画面剧情内容。\n"
                                "重要要求：\n"
                                "1.画面人物精准对应剧中角色，身份、样貌不得胡乱判定、随意替换。\n"
                                "2.画面人物、场景辨识度低则直接标注模糊/看不清，严禁主观臆测。\n"
                                "3.清晰写明场景、人物主体、动作神态、人物情绪与整体剧情氛围。\n"
                                "4.语言简洁准确，整体描述不超300字。\n"
                            )
                        enhanced_desc = self.multi_model.analyze_image(str(img_path), prompt)
                        desc['enhanced_description'] = enhanced_desc
                        print(str(i) + ' : ' + enhanced_desc)
                    except Exception as ex:
                        print(f'⚠ 多模型增强关键帧描述失败: {ex}')
            if not results:
                print('❌ 视频分析返回空结果')
                return None
            print(f'✅ 视频分析完成: {len(results.get("scenes", []))}个场景, {len(results.get("keyframes", []))}个关键帧')

            # 4. 智能场景筛选：评估场景质量并筛选高分场景
            try:
                from backend.engine.scene_scorer import score_and_filter_scenes
                scenes = results.get('scenes', [])
                # 获取目标时长（用于智能筛选）
                target_duration = config.get('target_duration') or None
                target_duration = float(target_duration) if target_duration else None
                # 收集对象检测结果
                objects_list = [obj_info.get('objects', []) for obj_info in results.get('objects', [])]
                # 执行评分和筛选
                if scenes and len(scenes) > 3:  # 只在场景数>3时才筛选
                    print(f'🧠 开始智能场景筛选: 原始{len(scenes)}个场景')
                    filtered_scenes = score_and_filter_scenes(
                        scenes=scenes,
                        video_path=video_path,
                        objects_list=objects_list if objects_list else None,
                        target_duration=target_duration
                    )
                    if filtered_scenes and len(filtered_scenes) < len(scenes):
                        # 筛选成功，更新结果
                        results['scenes'] = filtered_scenes
                        results['original_scenes'] = scenes  # 保留原始场景供参考
                        print(
                            f'✅ 智能筛选完成: '
                            f'{len(scenes)}个场景 → {len(filtered_scenes)}个高质量场景, '
                            f'平均评分: {np.mean([s.get("score", 0) for s in filtered_scenes]):.1f}'
                        )
                    else:
                        print('📌 场景质量均衡，无需筛选')
                else:
                    print(f'📌 场景数量较少({len(scenes)})，跳过筛选')
            except Exception as ex:
                print(f'⚠️智能场景筛选失败，使用原始场景: {ex}')

            # 5. 写入缓存（去除不可序列化字段）
            if cache_file:
                try:
                    safe_results = json.loads(
                        json.dumps(results, ensure_ascii=False, default=lambda o: None)
                    )
                    with cache_file.open('w', encoding='utf-8') as f:
                        json.dump(safe_results, f, ensure_ascii=False)
                    print(f'💾 已写入视频分析缓存: {cache_file}')
                except Exception as ex:
                    print(f'⚠ 写入视频分析缓存失败: {ex}')
            return results
        except Exception as ex:
            print(f'❌ 视频分析失败: {ex}')
            return None

    def _generate_script(self, vision_results: Dict, config: Dict, task_id: str) -> Optional[Dict]:
        """步骤2: AI生成解说文案"""
        try:
            # 1. 每次生成前都从全局状态获取最新的 ScriptGenerator，避免使用过期实例
            script_generator = self.script_generator
            if not script_generator:
                raise Exception('⚠ 文案生成引擎不可用，使用模板文案')
            print('============开始生成解说文案============')
            # 2. 根据前端传入的 llm 选择动态切换当前使用的 LLM 模型
            # print(config)
            # {'video_path': 'C:\\Users\\Administrator\\Downloads\\0519.mp4', 'script': '', 'voice': 'zh-CN-XiaoxiaoNeural', 'tts_engine': 'pyttsx3', 'auto_subtitle': True, 'auto_bgm': True, 'style': 'professional', 'subtitle_style': 'default', 'subtitle_position': 'bottom', 'subtitle_font_size': None, 'subtitle_font': None, 'subtitle_color': None, 'subtitle_bg_color': None, 'subtitle_stroke_color': None, 'subtitle_stroke_width': None, 'voice_volume': 100.0, 'bgm_volume': 30.0, 'original_audio_volume': 20.0}
            config = {"llm": "qwen", "sceneAccuracy": "medium", "emotionAnalysis": "deep", "scriptStyle": "suspense",
             "emotionTone": "reflective", "narrationMode": "film_3rd", "scriptStructure": "suspense",
             "targetAudience": "general", "scriptLength": "long", "creativityLevel": "moderate",
             "template": "film_explain", "target_duration_seconds": 153}
            # =====1======
            durationModeCommentary = 'full'  # 目标时长
            template = config.get('template')  # film_explain影视解说
            # =====2======
            visionModel = config.get('visionModel')  # 画面分析模型
            sceneAccuracyEl = config.get('sceneAccuracy')    # 场景识别精度
            emotionAnalysis = config.get('emotionAnalysis')   # 情感分析强度
            # =====3======
            llm = (config.get('llm') or None).strip()    # 文案生成llm
            scriptStyle = config.get('scriptStyle') or 'suspense'   # 文稿风格
            emotionTone = config.get('emotionTone') or 'dramatic'  # 情感基调
            narrationMode = config.get('narrationMode') or 'film_3rd'   # 解说类型
            scriptStructure = config.get('scriptStructure') or 'suspense'  # 文案结构complete
            targetAudience = config.get('targetAudience') or 'general'  # 目标人群
            scriptLength = config.get('scriptLength') or 'medium'   # 文稿长度
            creativityLevel = config.get('creativityLevel') or 'moderate'  # 创作深度
            # 目标时长：优先使用前端传入的 target_duration_seconds，其次使用视觉分析中的 duration
            target_duration = config.get('target_duration_seconds') or 100
            if target_duration is not None:
                target_duration = float(target_duration)
            # ========================
            style = scriptStyle
            narration_mode = (narrationMode or 'general').lower()
            emotion_tone = emotionTone
            structure = scriptStructure
            target_audience = targetAudience
            length = scriptLength
            creativity = creativityLevel
            print(template, emotion_tone, structure, target_audience, length, target_duration)
            # use_viral_prompts: 是否使用病毒式传播提示词（黄金三秒法则等）
            # 根据解说类型自动选择合适的开头钩子类型
            hook_type = 'suspense'  # 默认使用悬念式
            match narration_mode:
                case 'romance', 'animation_3rd':
                    # 情感/怀旧类，更适合情感共鸣型开头
                    hook_type = 'empathy'
                case 'film_3rd':
                    # 第三人称影视解说，突出剧情反转
                    hook_type = 'reversal'
                case 'documentary':
                    # 纪录片风，适合问题引导型或信息型开头
                    hook_type = 'question'
                case 'film_1st':
                    # 第一人称强代入，悬念式更抓人
                    hook_type = 'suspense'
                case 'suspense_twist':
                    # 悬疑反转专用，优先用悬念式
                    hook_type = 'suspense'
            print(style, narration_mode)
            
            vision_for_script = vision_results
            if target_duration:
                try:
                    scenes = vision_results.get('scenes') or []
                    new_scenes = []
                    for idx, sc in enumerate(scenes):
                        try:
                            sc_start = float(sc.get('start_time', 0.0) or 0.0)
                            sc_end = float(sc.get('end_time', sc_start) or sc_start)
                        except Exception:
                            sc_start, sc_end = 0.0, 0.0
                        # 完全超出目标时长的场景直接丢弃
                        if sc_start >= target_duration:
                            break
                        # 与目标时长有交集的最后一个场景，截断到目标时长
                        if sc_end > target_duration:
                            sc_end = target_duration
                        if sc_end <= sc_start:
                            continue
                        sc_new = dict(sc)
                        sc_new['start_time'] = float(sc_start)
                        sc_new['end_time'] = float(sc_end)
                        sc_new['duration'] = float(sc_end - sc_start)
                        new_scenes.append(sc_new)
                    # 按场景数量截断描述/情绪信息，避免与场景错位
                    desc_list = (vision_results.get('descriptions') or [])[:len(new_scenes)]
                    emo_list = (vision_results.get('emotions') or [])[:len(new_scenes)]
                    obj_list = (vision_results.get('objects') or [])[:len(new_scenes)]
                    vision_for_script = dict(vision_results)
                    vision_for_script['scenes'] = new_scenes
                    vision_for_script['descriptions'] = desc_list
                    vision_for_script['emotions'] = emo_list
                    vision_for_script['objects'] = obj_list
                    vision_for_script['duration'] = float(target_duration)
                except Exception as ex:
                    print(f'⚠ 基于目标时长截断场景失败，将使用完整视频分析: {ex}')
            # print(vision_for_script)

            # 将结构、长度、创意度等枚举值映射为更易理解的中文描述
            structure_map = {
                'complete': '完整起承转合结构',
                'outline': '提纲式要点结构',
                'three_act': '三幕式结构（开端-发展-高潮/结局）'
            }
            length_map = {
                'short': '整体字数偏短，控制在约100-200字',
                'medium': '标准长度，控制在约200-400字',
                'long': '内容更详细，控制在约400-800字'
            }
            creativity_map = {
                'low': '创意度偏保守，以事实和画面为主，少用夸张和网络梗',
                'moderate': '适度创意，在保证信息准确的前提下增强吸引力',
                'high': '创意度较高，可以合理虚构细节增强故事性，但不能违背画面内容'
            }
            audience_map = {
                'general': '面向大众观众，语言口语化、易懂',
                'kids': '面向儿童或家庭用户，语言温和、积极、避免复杂表达',
                'professional': '面向专业人士，可适度使用专业术语、逻辑更严谨'
            }
            structure_desc = structure_map.get(str(structure), str(structure))
            base_chars = None
            if target_duration:
                try:
                    base_chars = max(60, int(float(target_duration) * 3.5))
                except Exception:
                    base_chars = None
            if base_chars:
                length_str = str(length)
                if length_str == 'short':
                    min_chars = int(base_chars * 0.6)
                    max_chars = int(base_chars * 0.85)
                elif length_str == 'long':
                    min_chars = int(base_chars * 1.0)
                    max_chars = int(base_chars * 1.35)
                elif length_str == 'auto':
                    min_chars = int(base_chars * 0.8)
                    max_chars = int(base_chars * 1.1)
                else:
                    min_chars = int(base_chars * 0.75)
                    max_chars = int(base_chars * 1.05)
                length_desc = f'整体字数控制在约{min_chars}-{max_chars}字，使正常语速朗读时长尽量贴近剪辑后目标视频时长（约{target_duration:.0f}秒）。'
            else:
                length_desc = length_map.get(str(length), str(length))

            creativity_desc = creativity_map.get(str(creativity), str(creativity))
            audience_desc = audience_map.get(str(target_audience), str(target_audience))
            # 组合成交给大模型的自定义创作要求
            custom_requirements_lines = [
                f"- 模板/类型偏好：{template}（可以据此选择更贴合的叙事风格，例如影视解说/动画解说/纪录片解说等）",
                f"- 目标受众：{audience_desc}",
                f"- 文稿结构：{structure_desc}",
                f"- 文稿长度：{length_desc}",
                f"- 创意程度：{creativity_desc}",
                f"- 情感基调：整体情绪基调倾向于“{emotion_tone}”，请在措辞和节奏上体现这一点。"
            ]
            if target_duration:
                custom_requirements_lines.append(
                    f"- 目标整体时长：约{float(target_duration):.0f}秒，请控制文稿节奏和信息密度，使朗读时长与该目标大致匹配。"
                )
            custom_prompt = "\n".join(custom_requirements_lines)
            print(f'📝 调用文案生成器，目标时长: {target_duration}秒')
            script = script_generator.generate_script(
                vision_analysis=vision_for_script,
                style=style,
                duration=target_duration,
                narration_mode=narration_mode,
                custom_prompt=custom_prompt,
                hook_type=hook_type,
                use_viral_prompts=True
            )
            # 立即检查生成的文案字数
            if script and script.get('segments'):
                total_chars = sum(len(seg.get('text', '')) for seg in script['segments'])
                estimated_duration = total_chars / 3.5
                print(
                    f'📊 文案生成完成: 总字数={total_chars}字, '
                    f'预计时长={estimated_duration:.1f}秒, '
                    f'目标时长={target_duration}秒'
                )
                if target_duration and estimated_duration > target_duration * 1.2:
                    print(
                        f'❌ 文案严重超标！预计{estimated_duration:.1f}秒 > 目标{target_duration}秒的1.2倍，'
                        f'字数控制可能失败！'
                    )
            if not isinstance(script, dict):
                try:
                    script = json.loads(script)
                except Exception:
                    raise Exception('⚠ 文案生成结果不是结构化JSON')
            return script
        except Exception as ex:
            raise Exception(f'❌ 文案生成失败: {ex}')

    def _generate_voiceover(self, script: Dict[str, Any], config: Dict[str, Any], task_id: str) -> Optional[str]:
        """步骤3: 智能配音
        供完整流程 process_video 与 /api/commentary/generate-voiceover 调用。
        返回相对项目根目录的路径，例如: "output/commentary_audio_xxx.mp3"。
        """
        print(self.tts_engine)
        try:
            if not self.tts_engine:
                print('⚠️ TTS引擎不可用')
                return None
            full_text = ''
            # 1）优先按结构化 dict 解析（title + opening + segments + closing）
            if isinstance(script, dict):
                try:
                    parts = []
                    title = script.get('title') or ''
                    if title:
                        parts.append(title)
                    opening = script.get('opening') or ''
                    if opening:
                        parts.append(opening)
                    for seg in script.get('segments') or []:
                        text = seg.get('text') or ''
                        if text:
                            parts.append(text)
                    closing = script.get('closing') or ''
                    if closing:
                        parts.append(closing)
                    full_text = "\n".join(parts).strip()
                except Exception as ex:
                    # 结构化解析失败时，退回到纯文本模式，避免 AttributeError: 'str' object has no attribute 'get'
                    print(f'⚠ 脚本结构化解析失败，将按纯文本处理: {ex}')
                    try:
                        full_text = str(script).strip()
                    except Exception:
                        full_text = ''
            # 2）如果不是 dict，或上一步未能成功生成文本，则退回到字符串处理
            if not full_text:
                if isinstance(script, str):
                    full_text = script.strip()
                else:
                    try:
                        full_text = str(script).strip()
                    except Exception:
                        full_text = ''
            if not full_text:
                raise Exception('脚本内容为空，无法生成配音')

            # 输出到项目根目录下的 output/commentary_audio_*.mp3，便于前端通过 /output 静态路由访问
            file_name = f"commentary_audio_{int(time.time())}_{uuid.uuid4().hex[:6]}.mp3"
            rel_path = f"output/{file_name}"
            out_path = PROJECT_ROOT / 'output' / file_name
            out_path.parent.mkdir(parents=True, exist_ok=True)

            # 获取音色参数
            voice = 'zh-CN-XiaoxiaoNeural'
            # 原创解说流程强制使用本地 pyttsx3 引擎，不再调用 Edge-TTS / gTTS / Azure 等在线引擎
            available = list(getattr(self.tts_engine, 'available_engines', []) or [])
            if 'pyttsx3' not in available:
                print('⚠ 全局引擎列表中未声明 pyttsx3，将直接尝试调用本地 pyttsx3 引擎')
            engine0 = 'pyttsx3'
            # 1）首选且唯一的 TTS 引擎：本地 pyttsx3
            try:
                print(f'🎵 正在调用 {engine0} 引擎，音色: {voice}')
                success = self.tts_engine.synthesize(
                    text=full_text, output_path=str(out_path),
                    engine=engine0, voice=voice,
                    rate='+0%', volume='+0%'
                )
                if success:
                    print(f'✅ {engine0} 引擎合成成功')
            except Exception as ex:
                print(f"❌ 首选 TTS 引擎({engine0}) 合成失败: {ex}")
                success = False
            print(success, out_path)

            # 2）额外的兜底再尝试一次 pyttsx3（极端情况下前一次调用写盘失败）
            if not success or not out_path.exists():
                try:
                    print('🎵 首次调用失败，再次尝试本地 pyttsx3 引擎兜底')
                    success = self.tts_engine.synthesize(
                        text=full_text, output_path=str(out_path),
                        engine='pyttsx3', voice=voice,
                        rate='+0%', volume='+0%'
                    )
                except Exception as ex:
                    print(f"❌ 本地 pyttsx3 兜底合成仍然失败: {ex}")
                    success = False

            if not success or not out_path.exists():
                raise Exception('配音文件生成失败')

            # 读取配音实际时长，用于重新调整字幕时间轴（直接使用 ffprobe，兼容音频文件）
            try:
                cmd = [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    str(out_path)
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                actual_audio_duration = 0.0
                if result.returncode == 0:
                    dur_str = (result.stdout or '').strip()
                    try:
                        if dur_str:
                            actual_audio_duration = float(dur_str)
                    except Exception:
                        actual_audio_duration = 0.0
                if actual_audio_duration > 0:
                    print(f'✅ 配音生成完成: {rel_path}，实际时长: {actual_audio_duration:.2f}秒')
                    # 将实际时长保存到全局变量，供后续字幕调整使用
                    if not hasattr(self, '_audio_duration_cache'):
                        self._audio_duration_cache = {}
                    self._audio_duration_cache[task_id] = actual_audio_duration
                else:
                    print('⚠ ffprobe 未能读取配音时长，将按脚本文本估算')
            except Exception as ex:
                print(f'⚠ 无法读取配音时长(ffprobe调用失败): {ex}')
            return rel_path
        except Exception as ex:
            print(f'❌ 配音生成失败: {ex}')
            return None

    def _sync_all(self, video_path: str, audio_path: str, script: Dict,
                  vision_results: Dict, task_id: str) -> Optional[Dict]:
        """步骤4: 三同步处理"""
        print('=====开始执行三同步=====')
        try:
            if not self.sync_engine:
                print('⚠ 同步引擎不可用')
                return None
            # 在同步前，先根据配音实际时长重新调整字幕时间轴
            actual_audio_duration = getattr(self, '_audio_duration_cache', {}).get(task_id)
            if actual_audio_duration and script and isinstance(script, dict):
                segments = script.get('segments') or []
                if segments:
                    # 计算原始 segments 的总时长
                    original_duration = max(seg.get('end_time', 0) for seg in segments) if segments else 0
                    if original_duration > 0 and abs(actual_audio_duration - original_duration) > 1.0:
                        print(
                            f'⚠ 配音实际时长({actual_audio_duration:.2f}s)与原始场景时长({original_duration:.2f}s)'
                            f'差异较大，重新调整字幕时间轴'
                        )
                        # 按比例调整每个 segment 的时间
                        scale = actual_audio_duration / original_duration
                        for seg in segments:
                            try:
                                old_start = float(seg.get('start_time', 0))
                                old_end = float(seg.get('end_time', old_start))
                                seg['start_time'] = old_start * scale
                                seg['end_time'] = old_end * scale
                            except Exception as ex:
                                print(f'⚠ 调整segment时间失败: {ex}')
                        print(f'✅ 已根据配音实际时长重新调整字幕时间轴')
            # 执行三同步
            sync_results = self.sync_engine.sync_all(
                video_path=video_path,
                audio_path=audio_path,
                script=script,
                vision_analysis=vision_results
            )
            print(f'======三同步执行完成======')
            return sync_results
        except Exception as ex:
            print(f'❌ 三同步失败: {ex}')
            return None

    def _compose_final_video(self, video_path: str, audio_path: str, script: Dict,
                             sync_results: Dict, config: Dict, task_id: str) -> Optional[str]:
        """步骤5: 合成最终视频"""
        try:
            print('🎬 开始合成最终视频...')
            base_dir = PROJECT_ROOT
            output_dir = base_dir / 'output' / 'video'
            output_dir.mkdir(parents=True, exist_ok=True)

            video_path_obj = Path(video_path)
            if not video_path_obj.is_absolute():
                video_path_obj = base_dir / video_path_obj
            print(video_path_obj)

            audio_path_obj = Path(audio_path)
            if not audio_path_obj.is_absolute():
                audio_path_obj = base_dir / audio_path_obj
            print(audio_path_obj)

            # 获取配音实际时长，用于剪辑视频和调整字幕
            audio_duration = 0.0
            try:
                cmd = [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    str(audio_path_obj)
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    dur_str = (result.stdout or '').strip()
                    if dur_str:
                        audio_duration = float(dur_str)
                print(f'🎵 配音实际时长: {audio_duration:.2f}秒')
            except Exception as e:
                print(f'⚠ 无法获取配音时长: {e}')

            # 如果有配音时长，先裁剪视频到配音时长
            clipped_video_path = str(video_path_obj)
            if audio_duration > 0:
                try:
                    from backend.engine.video_clipper import VideoClipper
                    clipper = VideoClipper()
                    clipped_video_path = str(output_dir / f"clipped_{task_id[:8]}.mp4")
                    clipper.clip_video_by_timestamp(
                        input_video=str(video_path_obj),
                        output_video=clipped_video_path,
                        start_time="00:00:00.000",
                        end_time=f"00:00:{audio_duration:06.3f}"
                    )
                    print(f'✂ 已将视频剪辑到配音时长: {audio_duration:.2f}秒')
                except Exception as e:
                    print(f'⚠ 视频剪辑失败，将使用原始视频: {e}')
                    clipped_video_path = str(video_path_obj)

            subtitle_path: Optional[str] = None
            auto_subtitle = bool(config.get('auto_subtitle', True))
            if auto_subtitle:
                narration_script: Optional[Dict[str, Any]] = None
                try:
                    subtitle_segments = (sync_results or {}).get('audio_text_sync', {}).get('subtitle_segments')
                except Exception:
                    subtitle_segments = None

                # 计算脚本预估时长
                script_duration = 0.0
                if script.get('segments'):
                    last_segment = script['segments'][-1]
                    script_duration = float(last_segment.get('end_time', 0.0))

                # 时间轴缩放因子：如果配音时长与脚本时长不一致，需要调整字幕时间
                time_scale = 1.0
                if audio_duration > 0 and script_duration > 0:
                    time_scale = audio_duration / script_duration
                    if abs(time_scale - 1.0) > 0.01:  # 差异超过1%才调整
                        print(f'⏰ 配音时长({audio_duration:.2f}s)与脚本时长({script_duration:.2f}s)不一致，时间轴缩放: {time_scale:.4f}')

                if subtitle_segments:
                    narrations = []
                    for seg in subtitle_segments:
                        start = float(seg.get('start', seg.get('start_time', 0.0)))
                        end = float(seg.get('end', seg.get('end_time', start)))
                        # 应用时间轴缩放
                        start *= time_scale
                        end *= time_scale
                        # 确保结束时间不超过配音时长
                        if end > audio_duration:
                            end = audio_duration
                        text = seg.get('text', '')
                        time_range = f"{start:.3f}s-{end:.3f}s"
                        narrations.append({'time_range': time_range, 'text': text})
                    if narrations:
                        narration_script = {'narrations': narrations}
                else:
                    segments = script.get('segments') or []
                    narrations = []
                    for seg in segments:
                        start = float(seg.get('start_time', 0.0))
                        end = float(seg.get('end_time', start))
                        # 应用时间轴缩放
                        start *= time_scale
                        end *= time_scale
                        # 确保结束时间不超过配音时长
                        if end > audio_duration:
                            end = audio_duration
                        text = seg.get('text', '')
                        time_range = f"{start:.3f}s-{end:.3f}s"
                        narrations.append({'time_range': time_range, 'text': text})
                    if narrations:
                        narration_script = {'narrations': narrations}

                if narration_script:
                    try:
                        srt_path = output_dir / f"commentary_{int(time.time())}_{uuid.uuid4().hex[:6]}.srt"
                        generator = SubtitleGenerator()
                        subtitle_path = generator.generate_srt_from_script(narration_script, str(srt_path))
                    except Exception as se:
                        print(f'❌ 生成字幕失败: {se}')
                        subtitle_path = None

            bgm_path: Optional[str] = None
            if config.get('auto_bgm'):
                # 优先使用配置中的BGM路径
                bgm_value = config.get('bgm')
                if bgm_value:
                    bgm_obj = Path(bgm_value)
                    if not bgm_obj.is_absolute():
                        bgm_obj = base_dir / bgm_obj
                    if bgm_obj.exists():
                        bgm_path = str(bgm_obj)
                    else:
                        print(f'指定的BGM文件不存在: {bgm_obj}')
                else:
                    # 未显式指定BGM时，尝试使用默认背景音乐 backend/assets/audio/default_bgm.mp3
                    default_bgm = AUDIO_DIR / 'default_bgm.mp3'
                    if default_bgm.exists():
                        bgm_path = str(default_bgm)
                        print(f'🎵 自动BGM已启用，使用默认背景音乐: {default_bgm}')
                    else:
                        candidates = []
                        try:
                            for ext in ('.mp3', '.wav', '.m4a', '.flac', '.ogg'):
                                candidates.extend(AUDIO_DIR.glob(f'**/*{ext}'))
                        except Exception as se:
                            print(f'自动BGM搜索资源失败: {se}')
                            candidates = []
                        if candidates:
                            try:
                                candidates = sorted(candidates, key=lambda p: str(p))
                            except Exception:
                                pass

                            preferred = [p for p in candidates if p.name.lower().startswith(('bgm_', 'default_'))]
                            chosen = preferred[0] if preferred else candidates[0]
                            bgm_path = str(chosen)
                            print(f'🎵 自动BGM已启用，从音频资源目录选择: {chosen}')
                        else:
                            print(f'自动BGM已启用，但未提供bgm且默认BGM文件不存在，且音频资源目录为空: {AUDIO_DIR}')

            # 计算目标时长：优先使用前端传入的 target_duration_seconds，并结合源视频时长进行夹紧
            target_duration: Optional[float] = None
            source_duration: Optional[float] = None

            try:
                td_val = config.get('target_duration_seconds')
                if td_val is not None:
                    target_duration = float(td_val)
            except Exception:
                target_duration = None

            try:
                sd_val = config.get('source_duration_seconds')
                if sd_val is not None:
                    source_duration = float(sd_val)
            except Exception:
                source_duration = None

            # 如未显式提供源视频时长，则尝试在后端探测一次
            if source_duration is None or source_duration <= 0:
                try:
                    vp = VideoProcessor()
                    info = vp.get_video_info(str(video_path_obj)) or {}
                    src_dur = float(info.get('duration') or 0.0)
                    if src_dur > 0:
                        source_duration = src_dur
                except Exception as e:
                    print(f'⚠️ 获取源视频时长失败，将跳过基于源时长的夹紧: {e}')

            max_duration_for_merge: Optional[float] = None
            if target_duration is not None:
                # 基本下限保护
                if target_duration < 1.0:
                    target_duration = 1.0
                # 不超过源视频
                if source_duration and source_duration > 0 and target_duration > source_duration:
                    print(
                        '目标时长 %.2fs 大于源视频时长 %.2fs，已在合成阶段自动夹紧',
                        target_duration,
                        source_duration,
                    )
                    target_duration = source_duration

                max_duration_for_merge = target_duration

            output_file = output_dir / f"commentary_{int(time.time())}_{uuid.uuid4().hex[:6]}.mp4"

            # 读取字幕样式相关配置：样式预设 / 位置 / 字号
            subtitle_style_name = (config.get('subtitle_style')
                                   or config.get('subtitleStyle')
                                   or 'large')
            subtitle_position_conf = config.get('subtitle_position') or config.get('subtitlePosition')
            subtitle_font_size_conf = config.get('subtitle_font_size') or config.get('subtitleFontSize')
            subtitle_font_conf = config.get('subtitle_font') or config.get('subtitleFont')
            subtitle_color_conf = config.get('subtitle_color') or config.get('subtitleColor')
            subtitle_bg_color_conf = config.get('subtitle_bg_color') or config.get('subtitleBgColor')
            subtitle_stroke_color_conf = config.get('subtitle_stroke_color') or config.get('subtitleStrokeColor')
            subtitle_stroke_width_conf = config.get('subtitle_stroke_width') or config.get('subtitleStrokeWidth')

            options: Dict[str, Any] = {
                # 仅当生成了有效的字幕文件且开启了自动字幕时才启用字幕
                'subtitle_enabled': bool(subtitle_path) and bool(config.get('auto_subtitle', True)),
                'keep_original_audio': False,
                # 原创解说默认使用更醒目的“大号字幕”样式，如前端选择则按选择覆盖
                'subtitle_style': subtitle_style_name or 'large',
            }

            # 允许前端覆盖字幕位置
            if subtitle_position_conf:
                options['subtitle_position'] = str(subtitle_position_conf)

            # 允许前端覆盖字幕字体大小（数值合法时生效）
            try:
                if subtitle_font_size_conf is not None:
                    fs_val = int(float(subtitle_font_size_conf))
                    if fs_val > 0:
                        options['subtitle_font_size'] = fs_val
            except Exception:
                pass

            # 高级字幕样式覆盖：字体 / 颜色 / 描边 / 背景
            if subtitle_font_conf:
                try:
                    options['subtitle_font'] = str(subtitle_font_conf)
                except Exception:
                    pass

            if subtitle_color_conf:
                try:
                    options['subtitle_color'] = str(subtitle_color_conf)
                except Exception:
                    pass

            if subtitle_bg_color_conf:
                try:
                    options['subtitle_bg_color'] = str(subtitle_bg_color_conf)
                except Exception:
                    pass

            if subtitle_stroke_color_conf:
                try:
                    options['stroke_color'] = str(subtitle_stroke_color_conf)
                except Exception:
                    pass

            try:
                if subtitle_stroke_width_conf is not None:
                    sw_val = int(float(subtitle_stroke_width_conf))
                    if sw_val >= 0:
                        options['stroke_width'] = sw_val
            except Exception:
                pass

            # 若存在合法目标时长，则传递给合成器在加载后裁剪视频长度
            if max_duration_for_merge is not None and max_duration_for_merge > 0:
                options['max_duration'] = float(max_duration_for_merge)

            # 从 config 中读取音量控制参数
            voice_volume_conf = config.get('voice_volume')
            bgm_volume_conf = config.get('bgm_volume')
            original_volume_conf = config.get('original_audio_volume')

            if voice_volume_conf is not None:
                try:
                    options['voice_volume'] = float(voice_volume_conf)
                except Exception:
                    pass

            if bgm_volume_conf is not None:
                try:
                    options['bgm_volume'] = float(bgm_volume_conf)
                except Exception:
                    pass

            if original_volume_conf is not None:
                try:
                    options['original_audio_volume'] = float(original_volume_conf)
                except Exception:
                    pass

            composer = VideoComposer()
            composed_path = composer.merge_materials(
                video_path=clipped_video_path,  # 使用裁剪后的视频路径
                audio_path=str(audio_path_obj),
                output_path=str(output_file),
                subtitle_path=subtitle_path,
                bgm_path=bgm_path,
                options=options,
            )
            try:
                rel_path = Path(composed_path).resolve().relative_to(base_dir)
                rel_str = str(rel_path).replace('\\', '/')
            except Exception:
                rel_str = str(output_file).replace('\\', '/')
            print(f'✅ 视频合成完成: {rel_str}')
            return rel_str
        except Exception as e:
            print(f'❌ 视频合成失败: {e}')
            return None


def main():
    # data = {'name': '111111111', 'video_path': 'E:\\BaiduDownload\\12.mp4'}
    data = {'name': '111111111', 'video_path': 'C:\\Users\\Administrator\\Downloads\\0519.mp4'}
    video = CommentaryServiceEnhanced()
    # res = video.create_project(data)
    # print(res_create)
    res = {'code': 0, 'msg': '项目创建成功', 'data': {'project_id': '08951a10-2cbf-4178-87d3-b0786a5ca368', 'project': {'id': '08951a10-2cbf-4178-87d3-b0786a5ca368', 'name': '111111111', 'type': 'commentary', 'description': 'AI原创解说剪辑', 'status': 'draft', 'config': '{"template": "commentary", "output_format": "mp4", "quality": "high"}'}, 'config': {'video_path': 'C:\\Users\\Administrator\\Downloads\\0519.mp4', 'script': '', 'voice': 'zh-CN-XiaoxiaoNeural', 'tts_engine': 'pyttsx3', 'auto_subtitle': True, 'auto_bgm': True, 'style': 'professional', 'subtitle_style': 'default', 'subtitle_position': 'bottom', 'subtitle_font_size': None, 'subtitle_font': None, 'subtitle_color': None, 'subtitle_bg_color': None, 'subtitle_stroke_color': None, 'subtitle_stroke_width': None, 'voice_volume': 100.0, 'bgm_volume': 30.0, 'original_audio_volume': 20.0}}}
    res_process = video.process_video(res['data']['project']['id'], data['video_path'], res['data']['config'])

    print(res_process)


if __name__ == '__main__':
    start_time = time.time()
    try:
        main()
    except Exception as ex:
        print(f"程序崩溃: {ex}")
    elapsed = time.time() - start_time
    print(f"执行时间: {elapsed:.2f} 秒")
    time.sleep(10)


