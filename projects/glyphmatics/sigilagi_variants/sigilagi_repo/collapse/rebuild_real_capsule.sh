python3 ~/collapse/build_capsule.py \
  --source-dir ~/sigilagi_real \
  --module proxy_pointer_rag.py \
  --module system_refiner.py \
  --module sigil_stack.py \
  --entry-module sigil_stack.py \
  --entry-class SigilAGIStack \
  --entry-method demo \
  --output ~/sigilagi_real_capsule.py \
  --metadata-json '{"name":"sigilagi-real","version":"v2","slice":"core-control-retrieval"}'

python3 ~/sigilagi_real_capsule.py --verify-only
python3 ~/sigilagi_real_capsule.py --out ~/sigilagi_real_out
