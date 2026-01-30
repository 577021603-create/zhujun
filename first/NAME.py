import re
import os
import datetime


def extract_report_code(html_content):
    """提取window.__REPORT_DATA__=至window.__IS_STATIC_REPORT__=!0之间的代码"""
    pattern = r'window\.__REPORT_DATA__\s*=\s*([\s\S]*?)window\.__IS_STATIC_REPORT__\s*=\s*!0'
    match = re.search(pattern, html_content)

    if match:
        code_snippet = match.group(1).strip()
        print(f"成功截取代码片段（长度: {len(code_snippet)} 字符）")
        return code_snippet
    else:
        print("未找到匹配的代码块")
        return None


def extract_timestamps_from_code(code):
    """截取endTime后22个字符并提取时间戳"""
    if not code:
        return []

    timestamps = []
    endtime_positions = [m.start() for m in re.finditer(r'endTime', code)]

    print(f"\n找到 {len(endtime_positions)} 个endTime出现位置")

    for pos in endtime_positions:
        # 从endTime后开始截取22个字符
        start_index = pos + len('endTime')
        end_index = start_index + 22
        snippet = code[start_index:end_index]

        print(f"endTime位置 {pos}: 截取的22个字符为 '{snippet}'")

        # 从截取的字符中提取13位数字
        timestamp_match = re.search(r'(\d{13})', snippet)
        if timestamp_match:
            ts_str = timestamp_match.group(1)
            ts = int(ts_str)
            timestamps.append(ts)
            print(f"  → 成功提取时间戳: {ts_str}")
        else:
            print("  → 未找到13位数字")

    print(f"\n从代码片段中提取到 {len(timestamps)} 个有效时间戳")
    return timestamps


def convert_to_utc8(timestamp):
    """将时间戳转换为UTC+8时区的可读时间"""
    # 处理毫秒级时间戳
    timestamp_sec = timestamp / 1000
    # 转换为UTC时间
    utc_time = datetime.datetime.utcfromtimestamp(timestamp_sec)
    # 转换为UTC+8时间
    utc8_time = utc_time + datetime.timedelta(hours=8)
    return utc8_time.strftime("%Y-%m-%d %H:%M:%S")


def process_file(html_file_path):
    """处理单个HTML文件"""
    try:
        print(f"\n==== 处理文件: {html_file_path} ====")

        # 读取HTML文件
        with open(html_file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()

        # 提取报告代码块
        report_code = extract_report_code(html_content)
        if not report_code:
            print("跳过此文件")
            return

        # 提取所有可能的时间戳
        timestamps = extract_timestamps_from_code(report_code)
        if not timestamps:
            print("未找到时间戳，跳过此文件")
            return

        # 打印所有时间戳及其转换后的时间
        print("\n提取到的时间戳及其UTC+8时间:")
        for ts in timestamps:
            print(f"时间戳: {ts} → UTC+8时间: {convert_to_utc8(ts)}")

        # 使用第一个时间戳作为重命名依据
        first_timestamp = timestamps[0]
        utc8_time = convert_to_utc8(first_timestamp)

        # 替换时间中的冒号为下划线（Windows文件名不允许冒号）
        safe_time = utc8_time.replace(':', '_')

        # 获取文件基本信息
        file_dir = os.path.dirname(html_file_path)
        file_base = os.path.basename(html_file_path)
        file_name, file_ext = os.path.splitext(file_base)

        # 截取原文件名的前4个字符
        short_name = file_name[:4] if len(file_name) >= 4 else file_name

        # 生成新文件名（格式：前4字符_安全时间.扩展名）
        new_file_name = f"{short_name}_{safe_time}{file_ext}"
        new_file_path = os.path.join(file_dir, new_file_name)

        # 重命名文件
        os.rename(html_file_path, new_file_path)
        print(f"\n文件已重命名为: {new_file_name}")

    except Exception as e:
        print(f"处理文件时出错: {e}")


def main():
    """主函数：遍历目录并处理所有HTML文件"""
    directory = r"D:\TEST"

    # 检查目录是否存在
    if not os.path.exists(directory):
        print(f"错误：目录 '{directory}' 不存在")
        return

    print(f"开始处理目录: {directory}")

    # 获取目录下的所有文件
    files = os.listdir(directory)

    # 遍历并处理每个文件
    for file in files:
        file_path = os.path.join(directory, file)

        # 只处理文件，跳过子目录
        if os.path.isfile(file_path):
            process_file(file_path)

    print(f"\n完成处理目录: {directory}")


if __name__ == "__main__":
    main()