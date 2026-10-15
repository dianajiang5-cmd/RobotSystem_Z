import os
import sys
import subprocess

def run_command(command, description):
    print(f"\n{'='*50}")
    print(f"执行: {description}")
    print(f"命令: {command}")
    print('='*50)
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print("✓ 成功")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("✗ 失败")
        print(f"错误信息: {e.stderr}")
        return False

def main():
    print("🚀 机器人管理系统一键启动脚本")
    
    # 检查Python
    if not run_command("python --version", "检查Python"):
        print("请先安装Python并添加到环境变量")
        return
    
    # 安装依赖
    dependencies = [
        "django==4.2.7",
        "djangorestframework==3.14.0", 
        "django-cors-headers==4.3.1",
        "pillow"
    ]
    
    for dep in dependencies:
        if not run_command(f"pip install {dep}", f"安装 {dep}"):
            print(f"安装 {dep} 失败，尝试继续...")
    
    # 数据库迁移
    if not run_command("python manage.py makemigrations", "生成数据库迁移文件"):
        print("迁移文件生成失败")
        
    if not run_command("python manage.py migrate", "执行数据库迁移"):
        print("数据库迁移失败")
    
    # 检查是否已创建超级用户
    try:
        import django
        django.setup()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            print("\n创建默认管理员用户...")
            User.objects.create_superuser('admin', 'admin@example.com', '123456')
            print("✓ 管理员用户创建成功: 用户名: admin, 密码: 123456")
        else:
            print("✓ 管理员用户已存在")
    except Exception as e:
        print(f"用户创建检查失败: {e}")
    
    print("\n🎉 系统配置完成！")
    print("现在可以启动服务器了...")
    
    # 启动服务器
    run_command("python manage.py runserver", "启动开发服务器")

if __name__ == "__main__":
    main()