.PHONY: build upload test-upload clean

PACKAGE_NAME=dashscope-realtime

# 构建 wheel 和 sdist
build:
	@echo "📦 Building package..."
	python -m build

# 上传到 PyPI
upload: build
	@echo "🚀 Uploading to PyPI..."
	twine upload dist/*

# 上传到 Test PyPI
test-upload: build
	@echo "🧪 Uploading to TestPyPI..."
	twine upload --repository testpypi dist/*

# 清理构建缓存
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf dist/ build/ *.egg-info

# 本地安装自己打的包（可选）
install:
	pip install -e .

# 查看包内容（可选）
check:
	twine check dist/*

# 一键发布（可选）
release: clean upload
