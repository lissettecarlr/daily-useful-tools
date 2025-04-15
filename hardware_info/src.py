import psutil
import cpuinfo
import platform
import wmi
from datetime import datetime
from tabulate import tabulate
import os
import sys

def get_system_info():
    """获取系统基本信息"""
    info = {}
    info['系统'] = platform.system()
    info['系统版本'] = platform.version()
    info['系统架构'] = platform.machine()
    info['处理器'] = platform.processor()
    info['主机名'] = platform.node()
    return info

def get_cpu_info():
    """获取CPU详细信息"""
    info = {}
    try:
        cpu_info = cpuinfo.get_cpu_info()
        info['CPU型号'] = cpu_info.get('brand_raw', '未知')
        info['CPU核心数'] = psutil.cpu_count(logical=False)
        info['CPU线程数'] = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        info['CPU频率'] = f"{cpu_freq.current:.2f} MHz" if cpu_freq else "未知"
        info['CPU厂商'] = cpu_info.get('vendor_id_raw', '未知')
    except Exception as e:
        info['错误'] = f"获取CPU信息时出错: {str(e)}"
    return info

def get_detailed_memory_info():
    """获取详细的内存信息"""
    info = {}
    try:
        c = wmi.WMI()
        
        # 获取物理内存信息
        total_physical_memory = 0
        memory_modules = []
        
        for mem in c.Win32_PhysicalMemory():
            module = {}
            module['容量'] = f"{int(mem.Capacity) / (1024**3):.2f} GB"
            module['厂商'] = mem.Manufacturer if mem.Manufacturer else '未知'
            module['型号'] = mem.PartNumber if mem.PartNumber else '未知'
            module['速度'] = f"{mem.Speed} MHz" if mem.Speed else '未知'
            module['序列号'] = mem.SerialNumber if mem.SerialNumber else '未知'
            memory_modules.append(module)
            total_physical_memory += int(mem.Capacity)
        
        info['内存条数量'] = len(memory_modules)
        info['总物理内存'] = f"{total_physical_memory / (1024**3):.2f} GB"
        info['内存条详情'] = memory_modules
    except Exception as e:
        info['错误'] = f"获取内存信息时出错: {str(e)}"
    
    return info

def get_detailed_disk_info():
    """获取详细的磁盘信息"""
    info = {}
    try:
        c = wmi.WMI()
        
        # 获取物理磁盘信息
        for disk in c.Win32_DiskDrive():
            disk_info = {}
            disk_info['型号'] = disk.Model
            disk_info['接口类型'] = disk.InterfaceType
            disk_info['序列号'] = disk.SerialNumber
            disk_info['总容量'] = f"{int(disk.Size) / (1024**3):.2f} GB" if disk.Size else '未知'
            info[f'物理磁盘 {disk.DeviceID}'] = disk_info
    except Exception as e:
        info['错误'] = f"获取磁盘信息时出错: {str(e)}"

    return info

def get_motherboard_info():
    """获取主板详细信息"""
    info = {}
    try:
        c = wmi.WMI()
        
        for board in c.Win32_BaseBoard():
            info['主板厂商'] = board.Manufacturer
            info['主板型号'] = board.Product
            info['主板序列号'] = board.SerialNumber
            info['主板版本'] = board.Version
    except Exception as e:
        info['错误'] = f"获取主板信息时出错: {str(e)}"
    
    return info

def get_gpu_info():
    """获取显卡详细信息"""
    info = {}
    try:
        c = wmi.WMI()
        
        gpus = []
        # 虚拟设备的特征关键词
        virtual_keywords = ['Oray', 'LuminonCore', 'Twomon', 'Virtual', 'Remote', 'DisplayLink']
        
        for gpu in c.Win32_VideoController():
            # 跳过虚拟设备
            if any(keyword in gpu.Name for keyword in virtual_keywords):
                continue
                
            gpu_info = {}
            gpu_info['显卡名称'] = gpu.Name
            # 处理显存大小，如果为0或无效则显示为"共享显存"
            if gpu.AdapterRAM and int(gpu.AdapterRAM) > 0:
                gpu_info['显存大小'] = f"{int(gpu.AdapterRAM) / (1024**3):.2f} GB"
            else:
                gpu_info['显存大小'] = "共享显存"
            gpu_info['驱动版本'] = gpu.DriverVersion
            gpu_info['显卡厂商'] = gpu.AdapterCompatibility
            gpus.append(gpu_info)
        
        info['显卡数量'] = len(gpus)
        info['显卡详情'] = gpus
    except Exception as e:
        info['错误'] = f"获取显卡信息时出错: {str(e)}"
    return info

def print_hardware_info():
    """打印所有硬件信息"""
    try:
        print("\n=== 系统信息 ===")
        for key, value in get_system_info().items():
            print(f"{key}: {value}")
        
        print("\n=== CPU信息 ===")
        for key, value in get_cpu_info().items():
            print(f"{key}: {value}")
        
        print("\n=== 主板信息 ===")
        for key, value in get_motherboard_info().items():
            print(f"{key}: {value}")
        
        print("\n=== 内存信息 ===")
        memory_info = get_detailed_memory_info()
        if '错误' in memory_info:
            print(f"错误: {memory_info['错误']}")
        else:
            print(f"总物理内存: {memory_info['总物理内存']}")
     
            # 将内存条信息转换为表格形式
            memory_table = []
            headers = ['内存条', '容量', '厂商', '型号', '速度', '序列号']
            for i, module in enumerate(memory_info['内存条详情'], 1):
                memory_table.append([
                    i,
                    module['容量'],
                    module['厂商'],
                    module['型号'],
                    module['速度'],
                    module['序列号']
                ])
            print("\n内存条详情:")
            print(tabulate(memory_table, headers=headers, tablefmt='grid', maxcolwidths=[5, 10, 15, 20, 10, 15]))
        
        print("\n=== 显卡信息 ===")
        gpu_info = get_gpu_info()
        if '错误' in gpu_info:
            print(f"错误: {gpu_info['错误']}")
        else:
            # 将显卡信息转换为表格形式
            gpu_table = []
            headers = ['显卡', '名称', '显存大小', '驱动版本', '厂商']
            for i, gpu in enumerate(gpu_info['显卡详情'], 1):
                gpu_table.append([
                    i,
                    gpu['显卡名称'],
                    gpu['显存大小'],
                    gpu['驱动版本'],
                    gpu['显卡厂商']
                ])
            print(tabulate(gpu_table, headers=headers, tablefmt='grid', maxcolwidths=[5, 30, 10, 15, 15]))
        
        print("\n=== 磁盘信息 ===")
        disk_info = get_detailed_disk_info()
        if '错误' in disk_info:
            print(f"错误: {disk_info['错误']}")
        else:
            # 将磁盘信息转换为表格形式
            disk_table = []
            headers = ['磁盘', '型号', '接口类型', '序列号', '总容量']
            for i, (disk, info) in enumerate(disk_info.items(), 1):
                disk_table.append([
                    i,
                    info['型号'],
                    info['接口类型'],
                    info['序列号'],
                    info['总容量']
                ])
            print(tabulate(disk_table, headers=headers, tablefmt='grid', maxcolwidths=[5, 30, 10, 15, 10]))
    except Exception as e:
        print(f"打印硬件信息时发生错误: {str(e)}")

def is_frozen():
    """检查是否是PyInstaller打包的环境"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def main():
    # 设置工作目录，确保在打包后资源文件路径正确
    if is_frozen():
        os.chdir(os.path.dirname(sys.executable))
    
    try:
        print_hardware_info()
    except Exception as e:
        print(f"发生错误: {str(e)}")
    
    # 防止窗口立即关闭
    input("\n按回车键退出...")

if __name__ == "__main__":
    main() 