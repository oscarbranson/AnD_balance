.PHONY: distribute

distribute:
	python -m build
	twine upload dist/* 