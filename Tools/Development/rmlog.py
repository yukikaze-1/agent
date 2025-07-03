import os

def delete_log_files(directory):
    """
    递归删除指定目录下的所有 .log 文件
    :param directory: 要清理的根目录
    """
    # 检查目录是否存在
    if not os.path.exists(directory):
        print(f"目录 {directory} 不存在")
        return

    # 遍历目录及其子目录
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                os.remove(file_path)
                print(f"已删除: {file_path}")
            except Exception as e:
                print(f"删除 {file_path} 失败: {e}")
            # if file.endswith(".log"):
            #     file_path = os.path.join(root, file)
            #     try:
            #         os.remove(file_path)
            #         print(f"已删除: {file_path}")
            #     except Exception as e:
            #         print(f"删除 {file_path} 失败: {e}")

if __name__ == "__main__":
    # 指定要清理的目录
    log_directory = "./Log"
    delete_log_files(log_directory)
