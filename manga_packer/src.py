import os
import sys
import platform
import shutil
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 支持的图片格式
SUPPORTED_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.heic'}

def is_hidden_file(path):
    """判断文件是否为隐藏文件"""
    try:
        if not os.path.exists(path):
            return False
            
        name = os.path.basename(path)
                
        if name.startswith('.'):
            return True
        
        if platform.system() == "Windows":
            try:
                FILE_ATTRIBUTE_HIDDEN = 0x2
                try:
                    import win32api
                    import win32con
                    attrs = win32api.GetFileAttributes(path)
                    return bool(attrs & win32con.FILE_ATTRIBUTE_HIDDEN)
                except (ImportError, NameError):
                    try:
                        import ctypes
                        attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
                        return bool(attrs & FILE_ATTRIBUTE_HIDDEN)
                    except (ImportError, AttributeError):
                        try:
                            import stat
                            attrs = os.stat(path).st_file_attributes
                            return bool(attrs & stat.FILE_ATTRIBUTE_HIDDEN)
                        except (ImportError, AttributeError):
                            return name.startswith('.')
            except Exception:
                return False
        else:
            return name.startswith('.')
    except Exception as e:
        logger.error(f"隐藏检测异常 {path}: {str(e)}")
        return False

def validate_image_file(file_path):
    """验证图片是否完整且有效"""
    try:
        with Image.open(file_path) as img:
            img.verify()
        
        with Image.open(file_path) as img:
            img.load()
        
        return (file_path, None)
    except Exception as e:
        return (file_path, str(e))

def is_image_file(file_path):
    """判断文件是否为图片格式"""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in SUPPORTED_EXT

def scan_files(directory):
    """扫描目录下所有文件，区分图片和非图片"""
    image_files = []
    non_image_files = []
    
    try:
        if not os.path.exists(directory):
            logger.error(f"扫描目录不存在: {directory}")
            return image_files, non_image_files
            
        if not os.path.isdir(directory):
            logger.error(f"指定路径不是目录: {directory}")
            return image_files, non_image_files
        
        logger.info(f"开始扫描目录: {directory}")
        
        for root, dirs, files in os.walk(directory):
            try:
                dirs[:] = [d for d in dirs if not is_hidden_file(os.path.join(root, d))]
                
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        
                        if is_hidden_file(file_path):
                            continue
                        
                        if is_image_file(file_path):
                            image_files.append(file_path)
                        else:
                            non_image_files.append(file_path)
                    except Exception as e:
                        logger.error(f"处理文件时出错 {file}: {str(e)}")
            except Exception as e:
                logger.error(f"处理目录时出错 {root}: {str(e)}")
                continue
                
        logger.info(f"扫描完成: 找到 {len(image_files)} 个图片, {len(non_image_files)} 个非图片文件")
    except Exception as e:
        logger.error(f"扫描目录时出错: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
    
    return image_files, non_image_files

def validate_images(image_files, max_workers=None):
    """并行验证图片的有效性"""
    corrupted = []
    
    try:
        if not image_files:
            logger.info("没有找到图片文件，跳过验证")
            return corrupted
            
        if max_workers is None or max_workers <= 0:
            max_workers = os.cpu_count()
        
        logger.info(f"开始验证 {len(image_files)} 个图片文件")
        
        try:
            with tqdm(total=len(image_files), desc="验证图片", unit="file") as pbar:
                if len(image_files) < 100:
                    for path in image_files:
                        try:
                            path, error = validate_image_file(path)
                            if error:
                                corrupted.append({"path": path, "error": error})
                            pbar.update(1)
                        except Exception as e:
                            logger.error(f"验证图片失败 {path}: {str(e)}")
                            pbar.update(1)
                else:
                    try:
                        with ProcessPoolExecutor(max_workers=max_workers) as executor:
                            futures = {executor.submit(validate_image_file, path): path 
                                      for path in image_files}
                            
                            for future in as_completed(futures):
                                try:
                                    path, error = future.result()
                                    if error:
                                        corrupted.append({"path": path, "error": error})
                                    pbar.update(1)
                                except Exception as e:
                                    path = futures[future]
                                    logger.error(f"获取验证结果失败 {path}: {str(e)}")
                                    pbar.update(1)
                    except Exception as e:
                        logger.error(f"并行处理异常: {str(e)}")
        except Exception as e:
            logger.error(f"进度显示异常: {str(e)}")
    except Exception as e:
        logger.error(f"验证图片时出现错误: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
    
    return corrupted

def clean_files(directory, max_workers=None):
    """清理目录中的无效图片和非图片文件"""
    try:
        if not os.path.exists(directory):
            logger.error(f"清理目录不存在: {directory}")
            return 0, 0
            
        image_files, non_image_files = scan_files(directory)
        logger.info(f"发现图片文件: {len(image_files)}个, 非图片文件: {len(non_image_files)}个")
        
        corrupted_files = []
        try:
            corrupted_files = validate_images(image_files, max_workers)
            logger.info(f"发现损坏图片: {len(corrupted_files)}个")
        except Exception as e:
            logger.error(f"验证图片时出错: {str(e)}")
        
        deleted_corrupt = 0
        for item in corrupted_files:
            try:
                if os.path.exists(item["path"]):
                    os.remove(item["path"])
                    deleted_corrupt += 1
                    logger.info(f"已删除损坏图片: {item['path']} ({item['error']})")
            except Exception as e:
                logger.error(f"删除损坏图片失败 {item['path']}: {str(e)}")
        
        deleted_non_image = 0
        for file_path in non_image_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_non_image += 1
                    logger.info(f"已删除非图片文件: {file_path}")
            except Exception as e:
                logger.error(f"删除非图片文件失败 {file_path}: {str(e)}")
        
        logger.info(f"清理完成: 实际删除 {deleted_corrupt} 个损坏图片和 {deleted_non_image} 个非图片文件")
        return deleted_corrupt, deleted_non_image
    except Exception as e:
        logger.error(f"清理文件过程出错: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return 0, 0

def create_archive(source_dir, output_path):
    """创建ZIP压缩包"""
    try:
        if not os.path.exists(source_dir) or not os.path.isdir(source_dir):
            logger.error(f"源目录不存在或不是目录: {source_dir}")
            return False
        
        has_files = False
        for root, _, files in os.walk(source_dir):
            if files:
                has_files = True
                break
        
        if not has_files:
            logger.warning(f"源目录中没有任何文件: {source_dir}")
        
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        if not output_path.lower().endswith('.zip'):
            output_path = output_path.rstrip('.rar') + '.zip'
        
        base_name = output_path[:-4]
        root_dir = os.path.dirname(source_dir)
        base_dir = os.path.basename(source_dir)
        
        if not root_dir:
            root_dir = "."
        
        try:
            shutil.make_archive(base_name, 'zip', root_dir, base_dir)
            logger.info(f"已创建压缩包: {base_name}.zip")
            return True
        except PermissionError:
            logger.error(f"创建压缩包权限被拒绝: {base_name}.zip")
            return False
    except Exception as e:
        logger.error(f"创建压缩包异常: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

def categorize_by_image_count(source_dir, base_output_dir):
    """根据图片数量对漫画进行分类压缩"""
    parent_dir = os.path.join(base_output_dir, "分类结果")
    try:
        os.makedirs(parent_dir, exist_ok=True)
        
        long_dir = os.path.join(parent_dir, "长篇")
        medium_dir = os.path.join(parent_dir, "中篇")
        short_dir = os.path.join(parent_dir, "短篇")
        
        for dir_path in [long_dir, medium_dir, short_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        manga_dirs = []
        def collect_manga_dirs(current_dir):
            if not os.path.exists(current_dir):
                return
                
            for item in os.listdir(current_dir):
                item_path = os.path.join(current_dir, item)
                if os.path.isdir(item_path) and not is_hidden_file(item_path):
                    has_images = False
                    for root, _, files in os.walk(item_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if not is_hidden_file(file_path) and is_image_file(file_path):
                                has_images = True
                                break
                        if has_images:
                            break
                    
                    if has_images:
                        manga_dirs.append(item_path)
                    else:
                        collect_manga_dirs(item_path)
        
        collect_manga_dirs(source_dir)
        
        logger.info(f"发现漫画目录: {len(manga_dirs)}个")
        
        if not manga_dirs:
            logger.warning(f"在源目录中未找到任何漫画目录: {source_dir}")
            return
        
        for manga_dir in tqdm(manga_dirs, desc="处理漫画", unit="dir"):
            try:
                rel_path = os.path.relpath(manga_dir, source_dir)
                manga_name = rel_path.replace(os.sep, '_')
                
                image_count = 0
                for root, dirs, files in os.walk(manga_dir):
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            if not is_hidden_file(file_path) and is_image_file(file_path):
                                image_count += 1
                        except Exception as e:
                            logger.error(f"计算图片时出错 {file}: {str(e)}")
                
                if image_count >= 150:
                    output_dir = os.path.join(long_dir, manga_name)
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, f"{manga_name}.zip")
                elif image_count > 50:
                    output_path = os.path.join(medium_dir, f"{manga_name}.zip")
                else:
                    output_path = os.path.join(short_dir, f"{manga_name}.zip")
                
                logger.info(f"处理 '{manga_name}' (图片: {image_count}张)")
                if create_archive(manga_dir, output_path):
                    logger.info(f"成功创建压缩包: {output_path}")
                else:
                    logger.error(f"创建压缩包失败: {manga_name}")
            except Exception as e:
                logger.error(f"处理漫画目录时出错 {manga_dir}: {str(e)}")
                continue
    except Exception as e:
        logger.error(f"分类漫画时出错: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")

def generate_report(source_dir, output_dir, corrupted_count, non_image_count, elapsed_time):
    """生成处理报告并保存到输出目录"""
    try:
        report_path = os.path.join(output_dir, "处理报告.txt")
        
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        category_stats = {
            "长篇": 0,
            "中篇": 0, 
            "短篇": 0
        }
        
        category_dir = os.path.join(output_dir, "分类结果")
        if os.path.exists(category_dir):
            for category in category_stats.keys():
                category_path = os.path.join(category_dir, category)
                if os.path.exists(category_path):
                    if category == "长篇":
                        for dir_name in os.listdir(category_path):
                            dir_path = os.path.join(category_path, dir_name)
                            if os.path.isdir(dir_path):
                                for file in os.listdir(dir_path):
                                    if file.lower().endswith('.zip'):
                                        category_stats[category] += 1
                    else:
                        category_stats[category] = sum(1 for f in os.listdir(category_path) if f.lower().endswith('.zip'))
        
        total_manga = sum(category_stats.values())
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("================ 漫画处理报告 ================\n\n")
            f.write(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"处理耗时: {elapsed_time}\n\n")
            f.write(f"输入目录: {source_dir}\n")
            f.write(f"输出目录: {output_dir}\n\n")
            f.write("---------------- 清理统计 ----------------\n")
            f.write(f"删除损坏图片: {corrupted_count} 个\n")
            f.write(f"删除非图片文件: {non_image_count} 个\n\n")
            f.write("---------------- 分类统计 ----------------\n")
            f.write(f"处理漫画总数: {total_manga} 部\n")
            f.write(f"长篇漫画数量: {category_stats['长篇']} 部\n")
            f.write(f"中篇漫画数量: {category_stats['中篇']} 部\n")
            f.write(f"短篇漫画数量: {category_stats['短篇']} 部\n")
            
        return True
    except Exception as e:
        logger.error(f"生成报告时出错: {str(e)}")
        return False

def process_manga(source_dir, output_dir, max_workers):
    """处理漫画的主函数"""
    if not source_dir or not os.path.exists(source_dir):
        logger.error(f"输入目录无效或不存在: {source_dir}")
        return False
        
    if not output_dir:
        output_dir = os.getcwd()
        logger.warning(f"未指定输出目录，使用当前目录: {output_dir}")
    
    if max_workers is None or max_workers <= 0:
        max_workers = os.cpu_count()
        logger.info(f"未指定工作线程数，使用系统CPU核心数: {max_workers}")
    
    logger.info(f"输入目录: {source_dir}")
    logger.info(f"输出目录: {output_dir}")
    logger.info(f"最大并发数: {max_workers}")
    
    try:
        try:
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"成功创建输出目录: {output_dir}")
        except Exception as e:
            logger.error(f"创建输出目录失败: {str(e)}")
            return False
        
        start_time = datetime.now()
        
        logger.info("开始清理无效文件...")
        try:
            corrupted_count, non_image_count = clean_files(source_dir, max_workers)
            logger.info(f"清理完成! 已删除 {corrupted_count} 个损坏图片和 {non_image_count} 个非图片文件")
        except Exception as e:
            logger.error(f"清理文件过程出错: {str(e)}")
            corrupted_count, non_image_count = 0, 0
        
        logger.info("开始分类压缩...")
        try:
            categorize_by_image_count(source_dir, output_dir)
            logger.info("分类压缩完成!")
        except Exception as e:
            logger.error(f"分类压缩过程出错: {str(e)}")
        
        elapsed_time = datetime.now() - start_time
        logger.info(f"全部处理完成! 总耗时: {elapsed_time}")
        
        try:
            report_success = generate_report(source_dir, output_dir, corrupted_count, non_image_count, elapsed_time)
            if report_success:
                logger.info(f"处理报告已生成: {os.path.join(output_dir, '处理报告.txt')}")
            else:
                logger.warning("处理报告生成失败，但不影响主要处理流程")
        except Exception as e:
            logger.error(f"生成报告过程出错: {str(e)}")
        
        return True
    except Exception as e:
        logger.error(f"处理过程中发生错误: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1].lower() == '--help':
        print("用法: python src.py [漫画目录路径] [输出目录路径(可选)] [并发数(可选)]")
        sys.exit(0)

    if platform.system() != "Windows":
        print("此程序仅支持Windows系统")
        sys.exit(1)

    try:
        if len(sys.argv) > 1:
            source_dir = os.path.abspath(sys.argv[1])
            
            if len(sys.argv) >= 3:
                output_dir = os.path.abspath(sys.argv[2])
            else:
                output_dir = os.path.abspath(os.getcwd())
                
            max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else os.cpu_count()
            
            if not os.path.exists(source_dir):
                logger.error(f"输入目录不存在: {source_dir}")
                sys.exit(1)
                
            success = process_manga(source_dir, output_dir, max_workers)
            if not success:
                logger.error("处理过程出现错误")
                sys.exit(1)
        else:
            print("用法: python src.py [漫画目录路径] [输出目录路径(可选)] [并发数(可选)]")
            sys.exit(1)
    except Exception as e:
        logger.error(f"程序运行时发生错误: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main() 