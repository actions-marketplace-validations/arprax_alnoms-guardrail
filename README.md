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

## 🔄 The Developer Workflow

Alnoms is designed as a two-tier system to protect your infrastructure without slowing down your engineering velocity:

1. **The Guardrail (Fast & Broad):** During the GitHub Action, Alnoms runs in headless CI mode. It uses lightning-fast static analysis to scan dozens of changed files in milliseconds, instantly blocking the Pull Request if a critical bottleneck is found. 
2. **The Investigation (Deep & Narrow):** If the PR is blocked, the developer is instructed to run the engine locally on their machine using `alnoms analyze <file> --deep`. This shifts from static analysis to dynamic execution, providing a rich, interactive terminal report with empirical data to help them surgically fix the code before pushing a new commit.


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
## 🔓 Required Permissions

To allow the Alnoms bot to post the performance table directly to your Pull Request conversation, you must ensure the workflow has write access.

1. **In your YAML:** Ensure the `permissions` block is present (as shown in the Quick Start).
2. **In GitHub Settings:** - Navigate to **Settings > Actions > General**.
   - Under **Workflow permissions**, select **Read and write permissions**.
   - Click **Save**.

> [!CAUTION]
> If these permissions are not set, the action will still run, but you will see a `403 Forbidden` error in the logs and the PR comment will not appear.

---

## 🏢 Enterprise Intelligence

Arprax Enterprise users can connect their **Alnoms Guardrail** to the Arprax Dashboard to unlock advanced fiscal observability:

* **Regression Tracking:** Monitor how algorithmic complexity evolves across different team releases.
* **Empirical Cost Estimation:** Convert Big-O complexity into actual USD cost estimates based on your specific cloud provider's compute rates.
* **Deep Empirical Scans:** Automated triggers for `--deep` analysis on critical production paths.

---

## 🔬 Complexity Intelligence Logic

Alnoms doesn't just flag "slow" code; it identifies **Algorithmic Anti-Patterns** that lead to non-linear scaling:

| Complexity | Status | Risk Level | Example Pattern |
| :--- | :--- | :--- | :--- |
| $O(1) / O(\log N)$ | ✅ Pass | Optimal | Hash lookups, Binary search |
| $O(N)$ | ⚠️ Warning | Moderate | Membership tests (`in`) inside a single loop |
| $O(N^2)$ | ❌ Block | High | Nested loops, Incremental string/list concatenation |
| $O(N^3)$ | ❌ Block | Critical | Triple-nested loops, Matrix operations without optimization |

*Complexity is determined via static AST analysis and verified against the Arprax complexity heuristics engine.*

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


**Built with precision by [Arprax](https://arprax.com).