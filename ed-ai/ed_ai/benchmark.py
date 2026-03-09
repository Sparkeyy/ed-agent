#!/usr/bin/env python3
"""Benchmark Ollama models for Everdell AI opponent.

Tests models against criteria:
- Response time (target: <10s per turn)
- Response quality (can it parse valid actions?)
- Token throughput (tokens/sec)

Usage:
    python3 -m ed_ai.benchmark [--models phi4:14b,qwen2.5:14b,llama3.1:8b]
    python3 -m ed_ai.benchmark --host http://192.168.0.14:11434
"""

import argparse
import asyncio
import json
import time
import httpx


# Sample game state prompt (realistic ~1500 tokens)
SAMPLE_PROMPT = """=== EVERDELL - YOUR TURN ===
Season: Spring | Turn: 8 | You are: "AI Benchmark"

MY RESOURCES: 2🪵 3💧 1🪨 5🫐
MY WORKERS: 1 available / 3 total
MY CITY (4/15):
  Farm (Green Production, 1pt) | Twig Barge (Green Production, 1pt)
  Resin Refinery (Green Production, 1pt) | Mine (Green Production, 2pt)

MY HAND (5):
  [1] Castle (Purple Prosperity, 4pt, cost: 2🪵 3💧 3🪨) - Unique
  [2] Husband (Green Production, 2pt, cost: 3🫐) - pairs with Farm
  [3] Shopkeeper (Blue Governance, 1pt, cost: 2🫐) - Unique
  [4] Wanderer (Tan Traveler, 1pt, cost: 2🫐)
  [5] Barge Toad (Green Production, 1pt, cost: 2🫐) - pairs with Twig Barge

MEADOW:
  [1] Inn (Red, 2pt, 2🪵1💧) [2] Queen (Red, 4pt, 5🫐)
  [3] Crane (Blue, 1pt, 1🪨) [4] School (Purple, 2pt, 2🪵2💧)
  [5] Fair Grounds (Green, 3pt, 1🪵2💧1🪨) [6] Fool (Tan, -2pt, 3🫐)
  [7] Chapel (Red, 2pt, 2🪵1💧1🪨) [8] Doctor (Green, 4pt, 4🫐)

OPPONENTS:
  Human Player: 3🪵 0💧 2🪨 3🫐 | Workers 0/3 | City 5/15 | Hand 6

VALID ACTIONS:
  1. PLACE_WORKER at "2 Resin" → gain 2 resin
  2. PLAY_CARD "Husband" from hand (cost: 3🫐) - FREE via Farm!
  3. PLAY_CARD "Shopkeeper" from hand (cost: 2🫐)
  4. PLAY_CARD "Wanderer" from hand (cost: 2🫐)
  5. PLAY_CARD "Barge Toad" from hand (cost: 2🫐) - FREE via Twig Barge!
  6. PLAY_CARD "Inn" from meadow[1] (cost: 2🪵 1💧)
  7. PLAY_CARD "Crane" from meadow[3] (cost: 1🪨)
  8. PREPARE_FOR_SEASON → advance to Summer, gain 1 worker

Choose an action (respond with just the number):"""

SYSTEM_PROMPT = """You are an experienced Everdell player. Analyze the game state and choose the best action. Consider card synergies, resource efficiency, and point maximization. Respond with ONLY the action number."""


async def benchmark_model(host: str, model: str, num_runs: int = 5) -> dict:
    """Run benchmark for a single model."""
    results = {
        'model': model,
        'runs': [],
        'errors': 0,
        'valid_responses': 0,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(num_runs):
            start = time.time()
            try:
                resp = await client.post(f"{host}/api/generate", json={
                    'model': model,
                    'prompt': SAMPLE_PROMPT,
                    'system': SYSTEM_PROMPT,
                    'stream': False,
                    'options': {
                        'temperature': 0.3,
                        'num_predict': 100,
                    }
                })
                elapsed = time.time() - start

                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data.get('response', '')
                    eval_count = data.get('eval_count', 0)
                    eval_duration_ns = data.get('eval_duration', 1)
                    tokens_per_sec = eval_count / (eval_duration_ns / 1e9) if eval_duration_ns > 0 else 0

                    # Check if response contains a valid action number (1-8)
                    is_valid = any(str(n) in response_text for n in range(1, 9))

                    run = {
                        'elapsed_s': round(elapsed, 2),
                        'response': response_text.strip()[:200],
                        'tokens': eval_count,
                        'tokens_per_sec': round(tokens_per_sec, 1),
                        'valid_action': is_valid,
                    }
                    results['runs'].append(run)
                    if is_valid:
                        results['valid_responses'] += 1
                else:
                    results['errors'] += 1
                    results['runs'].append({'error': f"HTTP {resp.status_code}", 'elapsed_s': round(elapsed, 2)})
            except Exception as e:
                results['errors'] += 1
                results['runs'].append({'error': str(e), 'elapsed_s': round(time.time() - start, 2)})

    # Calculate aggregates
    successful = [r for r in results['runs'] if 'elapsed_s' in r and 'error' not in r]
    if successful:
        results['avg_latency_s'] = round(sum(r['elapsed_s'] for r in successful) / len(successful), 2)
        results['avg_tokens_per_sec'] = round(sum(r.get('tokens_per_sec', 0) for r in successful) / len(successful), 1)
        results['validity_rate'] = round(results['valid_responses'] / len(successful), 2)
    else:
        results['avg_latency_s'] = None
        results['avg_tokens_per_sec'] = None
        results['validity_rate'] = 0

    return results


async def check_model_available(host: str, model: str) -> bool:
    """Check if model is available, pull if not."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{host}/api/tags")
            if resp.status_code == 200:
                models = [m['name'] for m in resp.json().get('models', [])]
                return model in models or any(model.split(':')[0] in m for m in models)
        except Exception:
            pass
    return False


async def main():
    parser = argparse.ArgumentParser(description='Benchmark Ollama models for Everdell AI')
    parser.add_argument('--host', default='http://localhost:11434', help='Ollama host URL')
    parser.add_argument('--models', default='phi4:14b,qwen2.5:14b,llama3.1:8b',
                       help='Comma-separated list of models to test')
    parser.add_argument('--runs', type=int, default=5, help='Number of runs per model')
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(',')]

    print(f"Everdell AI Model Benchmark")
    print(f"   Host: {args.host}")
    print(f"   Models: {', '.join(models)}")
    print(f"   Runs per model: {args.runs}")
    print(f"   Target: <10s latency, >80% validity")
    print()

    all_results = []

    for model in models:
        print(f"Testing {model}...")
        available = await check_model_available(args.host, model)
        if not available:
            print(f"   Model not found locally. Pull with: ollama pull {model}")
            print(f"   Skipping.")
            continue

        result = await benchmark_model(args.host, model, args.runs)
        all_results.append(result)

        print(f"   Avg latency: {result['avg_latency_s']}s")
        print(f"   Avg tokens/sec: {result['avg_tokens_per_sec']}")
        print(f"   Valid responses: {result['validity_rate']*100:.0f}%")
        print(f"   Errors: {result['errors']}")
        print()

    # Summary
    print("=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"{'Model':<20} {'Latency':>8} {'Tok/s':>8} {'Valid%':>8} {'Pass?':>6}")
    print("-" * 60)

    best = None
    for r in all_results:
        latency = r['avg_latency_s'] or 'N/A'
        tps = r['avg_tokens_per_sec'] or 'N/A'
        valid = f"{r['validity_rate']*100:.0f}%" if r['validity_rate'] else 'N/A'

        passes = (r['avg_latency_s'] is not None and
                 r['avg_latency_s'] < 10 and
                 r['validity_rate'] >= 0.6)

        mark = 'PASS' if passes else 'FAIL'
        print(f"{r['model']:<20} {str(latency):>7}s {str(tps):>8} {str(valid):>8} {mark:>6}")

        if passes and (best is None or r['avg_latency_s'] < best['avg_latency_s']):
            best = r

    print()
    if best:
        print(f"Recommended model: {best['model']}")
        print(f"   Set OLLAMA_MODEL={best['model']} in ed-ai config")
    else:
        print("No model met all criteria. Consider:")
        print("   - Pulling smaller models: ollama pull phi4:14b")
        print("   - Increasing timeout")
        print("   - Using GPU acceleration")

    # Save results
    output_path = 'benchmark_results.json'
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nFull results saved to {output_path}")


if __name__ == '__main__':
    asyncio.run(main())
