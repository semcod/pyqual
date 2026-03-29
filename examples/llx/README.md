# LLX Integration Example

This example shows how to integrate **llx** for intelligent code generation within pyqual quality pipelines.

## Overview

LLX enhances pyqual by:
- Analyzing project metrics (files, lines, complexity, duplication)
- Selecting the optimal LLM model based on actual code metrics
- Generating targeted fixes using the selected model

## Files

- `pyqual-llx.yaml` - Complete pipeline configuration with llx integration
- `README.md` - This file

## Quick Start

1. Install dependencies:
   ```bash
   pip install llx[prellm] pyqual code2llm vallm
   ```

2. Copy the configuration:
   ```bash
   cp pyqual-llx.yaml ../../pyqual.yaml
   ```

3. Run the pipeline:
   ```bash
   cd ../..
   pyqual run
   ```

## How It Works

1. **Analyze**: `code2llm` collects project metrics
2. **Validate**: `vallm` identifies issues and creates error report
3. **Fix**: `llx fix` reads errors, selects optimal model, generates fixes
4. **Test**: Run tests to verify fixes
5. **Loop**: Repeat until all quality gates pass

## Model Selection

LLX automatically selects models based on project metrics:

| Project Size | Files | Lines | Selected Model |
|--------------|-------|-------|----------------|
| Small | <3 | <500 | Free (Gemini 2.5 Pro) |
| Medium | 3-10 | 500-5K | Cheap (Claude Haiku 4.5) |
| Large | 10-50 | 5K-20K | Balanced (Claude Sonnet 4) |
| Very Large | 50+ | 20K+ | Premium (Claude Opus 4) |

## Customization

See the [full documentation](https://github.com/wronai/llx/docs/PYQUAL_INTEGRATION.md) for:
- Custom model thresholds
- Advanced configuration options
- Error handling strategies
- Best practices
