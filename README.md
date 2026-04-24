# Alnoms Performance Guardrail 🚀

[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-Alnoms_Guardrail-blue.svg)](https://github.com/marketplace/actions/alnoms-performance-guardrail)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Stop expensive performance mistakes from reaching production.**

The Alnoms GitHub Action acts as a CI/CD FinOps compliance gate for your Python codebase. By detecting inefficient algorithmic patterns (like $O(N^2)$ or $O(N^3)$) early in the Pull Request cycle, Alnoms prevents code that will cause massive cloud compute spikes from ever being merged.

## 💡 How it Works

Instead of waiting for Datadog or AWS Cost Explorer to alert you that your infrastructure bill has doubled, Alnoms analyzes your code structure directly in the PR before deployment.

1. **Targeted Diffing:** Only analyzes the `.py` files changed in the active Pull Request to ensure lightning-fast CI runs.
2. **Deep Analysis:** Runs static and empirical complexity tests to map Big-O scaling limits.
3. **Automated Enforcement:** Posts a detailed impact report as a PR comment and intentionally fails the build if configured complexity thresholds are breached.

---

## 🛠️ Quick Start Integration

Add this workflow to your repository in `.github/workflows/alnoms-guardrail.yml`.

```yaml
name: Alnoms Cost Intelligence Guardrail

on:
  pull_request:
    paths:
      - '**.py' # Only trigger when Python files are changed

jobs:
  performance-audit:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0 # Required for Alnoms to perform git diff

      - name: Run Alnoms Guardrail
        uses: arpraxadmin/alnoms-action@main
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          fail_on: 'O(N^3)' # Block the PR if quadratic or worse is detected
```

## ⚙️ Configuration Inputs

| Input | Description | Required | Default |
| :--- | :--- | :--- | :--- |
| `github_token` | Automatically provided by GitHub Actions to post PR comments. | Yes | `${{ github.token }}` |
| `fail_on` | The complexity threshold that triggers a failed CI build (e.g., `O(N^2)`, `O(N^3)`). | No | `""` (Warn only) |
| `alnoms_api_key` | Arprax API key for Enterprise usage tracking and Deep Empirical Cost Estimation. | No | `""` |

## 📊 Example Output

When a bottleneck is detected, Alnoms posts a structured intelligence report directly to the PR:

> ❌ **Alnoms Performance Guardrail: Failed**
> 
> **File:** `data_pipeline/aggregator.py`  
> **Function:** `merge_orderbooks()`  
> **Detected Complexity:** `O(N^2)` (Quadratic)  
>
> **Cost Impact Warning:** This function contains an incremental concatenation loop. At production scale (100k+ rows), this will cause an exponential spike in compute cycles, potentially leading to container OOM kills and degraded service.
> 
> **Recommendation:** Utilize vectorized operations or pre-allocate memory buffers before merging.

---

**Built with precision by [Arprax](https://arprax.com).