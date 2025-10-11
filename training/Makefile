install:
	uv sync

process:
	uv run python process_all_videos.py

train:
	uv run python train_model.py

inference:
	uv run python realtime_inference.py

clean:
	rm -rf models/
	rm -rf .venv/
	rm -rf data/clips/
	rm -rf data/landmarks/
	rm -rf data/series/
