# Pedal Workshop — native-first task runner.
# The app is the product (native/); the pipeline is optional offline tooling.
.PHONY: help build run index status sync clean

help:
	@echo "Pedal Workshop"
	@echo "  make build    build + install + launch the macOS app (native/launch.sh)"
	@echo "  make run      alias for build"
	@echo "  make status   pipeline progress (extractions / review / done)"
	@echo "  make sync     reconcile the pipeline manifest with extractions on disk"
	@echo "  make index    regenerate the local schematic index seed (your library)"
	@echo "  make clean    remove build artifacts"

build run:
	cd native && ./launch.sh

status:
	python3 pipeline/manifest.py status

sync:
	python3 pipeline/manifest.py sync

# Regenerate the local (gitignored) schematic index from your own library.
index:
	python3 pipeline/tools/generate_native_index.py

clean:
	rm -rf native/.build native/PedalWorkshop.xcodeproj
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
