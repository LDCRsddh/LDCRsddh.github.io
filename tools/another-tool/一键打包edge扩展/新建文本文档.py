import os
import shutil
import json
import re
import argparse
from pathlib import Path

def sanitize_filename(name):
    """移除文件名中的非法字符"""
    return re.sub(r'[\\/*?:"<>|]', "", name)

def get_edge_extension_path():
    """获取Edge扩展程序的安装路径"""
    appdata = os.getenv('LOCALAPPDATA')
    if not appdata:
        raise FileNotFoundError("无法找到LOCALAPPDATA环境变量")
    
    edge_path = Path(appdata) / "Microsoft" / "Edge" / "User Data" / "Default" / "Extensions"
    if not edge_path.exists():
        raise FileNotFoundError(f"Edge扩展目录不存在: {edge_path}")
    return edge_path

def find_latest_version(extension_dir):
    """找到扩展的最新版本目录"""
    versions = [d for d in extension_dir.iterdir() if d.is_dir()]
    if not versions:
        return None
    
    # 按版本号排序（假设目录名是版本号）
    versions.sort(key=lambda x: [int(part) if part.isdigit() else part for part in x.name.split('.')], reverse=True)
    return versions[0]

def get_extension_name(manifest_path):
    """从manifest.json获取扩展名称"""
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
            # 尝试获取本地化名称或直接名称
            name = manifest.get("name")
            if name and name.startswith("__MSG_"):
                loc_key = name.replace("__MSG_", "").strip("__")
                locales = manifest.get("locales", {})
                default_locale = manifest.get("default_locale", "en")
                loc_file = manifest_path.parent / "_locales" / default_locale / "messages.json"
                
                if loc_file.exists():
                    with open(loc_file, 'r', encoding='utf-8') as lf:
                        messages = json.load(lf)
                        return messages.get(loc_key, {}).get("message", loc_key)
            return name if isinstance(name, str) else None
    except Exception as e:
        print(f"读取manifest失败: {e}")
    return None

def pack_extension(extension_id, version_dir, output_dir):
    """打包单个扩展程序"""
    manifest_path = version_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"跳过 {extension_id} (找不到manifest.json)")
        return
    
    ext_name = get_extension_name(manifest_path) or extension_id
    safe_name = sanitize_filename(ext_name)
    zip_filename = f"{safe_name}_{extension_id}.zip"
    zip_path = output_dir / zip_filename
    
    try:
        # 创建ZIP文件
        shutil.make_archive(
            base_name=str(zip_path.with_suffix('')),
            format='zip',
            root_dir=str(version_dir),
            verbose=False
        )
        print(f"已打包: {zip_filename}")
    except Exception as e:
        print(f"打包失败 [{ext_name}]: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='打包Edge浏览器所有扩展程序')
    parser.add_argument('-o', '--output', default='edge_extensions', 
                        help='输出目录 (默认: edge_extensions)')
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        ext_root = get_edge_extension_path()
        print(f"找到Edge扩展目录: {ext_root}")
        
        # 遍历所有扩展
        for ext_id_dir in ext_root.iterdir():
            if not ext_id_dir.is_dir():
                continue
                
            version_dir = find_latest_version(ext_id_dir)
            if not version_dir:
                print(f"跳过 {ext_id_dir.name} (找不到版本目录)")
                continue
                
            pack_extension(ext_id_dir.name, version_dir, output_dir)
            
        print(f"\n所有扩展已打包到: {output_dir.resolve()}")
    except Exception as e:
        print(f"程序出错: {str(e)}")
        input("按Enter键退出...")

if __name__ == "__main__":
    main()
