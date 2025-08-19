# Structured Argumentation for Trust in Agents

[Dockerfile](https://hub.docker.com/r/egecakar/edu-classifier-serverless)(The Docker container is made to support running locally and on a RunPod serverless instance)

Implementation of "The Argument is the Explanation: Structured Argumentation for Trust in Agents" (Under Review).

This repository provides a complete pipeline for converting multi-agent AI outputs into verifiable argument graphs using Bipolar Assumption-Based Argumentation (B-ABA), achieving state-of-the-art performance on AAEC argument extraction and strong results on AMT relation classification, while enabling automatic fact-checking and iterative refinement.

## Key Features

- **State-of-the-art Argument Mining**: 94.44 F1 on AAEC literal extraction (5.7 points above prior work)
- **New Best on Relation Classification**: 0.81 F1 on 3-class AMT relation classification (AMT 1 + 2 combined)
- **Multi-Agent Risk Assessment**: SWIFT (Structured What-If Technique) implementation with specialized expert agents
- **Bipolar ABA Framework**: Complete Python implementation with SAT-based extension solving -- will also be released as a separate Python package to use with managers!
- **Automatic Fact-Checking**: Detect contradictions via fact nodes attacking argument nodes
- **Feedback Loop**: Test-time refinement without retraining
- **Deployment Ready**: Docker container for relation classifier, fully local pipeline (except LLMs)

## Installation

```bash
# Clone the repository
git clone https://github.com/Ege-Cakar/Structured-Argumentation-For-Trust.git
cd Structured-Argumentation-For-Trust

# For relation classification (GPU recommended)
docker pull egecakar/edu-classifier-serverless
```

## Quick Start

### 1. Generate Risk Assessment Report
```python
python -m report_generator.src.main
```
You should modify the `dummy_req.md` file under with your request! Add database files under ./report_generator/data/database -- it supports PDF files with PyPDF2 and text files.

### 2. Extract Argumentative Literals
```python
python literal_extractor.py --input ./report_generator/data/report/sections_transformed.json
```
Either move sections_transformed into ./initial_files, or input its location under the report generator. Above shows the latter. By default, the output will go to ./intermediate_files.

### 3. Classify Relations
```python
python edge_classifier_v2.py --mode window --window_size 2
```
Use v2 for better overall performance, v1 is kept for backwards compatibility with certain things. It will by default take in ./intermediate_files/literals.json and output to ./intermediate_files/edges_classified.json.

### 4. Build Argument Graph
```python
python graph_generator.py 
```
Takes in edges_classified from its default location (also supports an --input argument), generates an html visualization, and finds 3 largest admissible extensions.

### 5. Fact-Check Arguments
```python
python fact_checker.py
```

Loads edges_classified, takes in facts.md from ./initial_files/facts.md, extracts literals, computes unidirectional edges, outputs an interactive html visualization, and computes 3 largest admissible extensions.

### 6. Generate Feedback
```python
python feedback_generator.py 
```
Generates feedback from the output of fact_checker.py and attaches it to the conversation file you have selected for resuming from that later on.

## Repository Structure

- `aba_pkg/` - Bipolar ABA Python package with SAT-based extension solving
- `report_generator/` - Multi-agent SWIFT risk assessment system
- `training_data/` - Fine-tuning datasets for literal extraction and relation classification -- for reproduction
- `initial_files/` - Initial files required for the graph pipeline
- `edge_classifier.py` - Original relation classifier
- `edge_classifier_v2.py` - Optimized classifier 
- `literal_extractor.py` - GPT-4.1 based literal extraction -> IMPORTANT: to use this file, you need a fine-tuned 4.1 mini on your OpenAI account. This can be done via the files under training_data -- our model will not work for you.
- `markdown_extractor.py` - Markdown/text file preprocessor for literal extraction
- `fact_checker.py` - Fact node integration and attack detection
- `feedback_generator.py` - Feedback generator for the iterative refinement system
- `graph_generator.py` - Interactive graph visualization with pyvis

## Models

### Pre-trained Models Available
- **Literal Extraction**: Fine-tuned GPT-4.1 and GPT-4.1-mini (via OpenAI API) (you need to train it yourself in the OpenAI api, but default settings with the files we provided will give you the same performance)
- **Relation Classification**: ModernBERT-large (Docker container) and GPT-4.1 (API) (same case with the 4.1 model here)

### Training Your Own
Training data and scripts are provided in `training_data/`. The formatted datasets are plug-and-play for fine-tuning:
- AAEC corpus for literal extraction (3 epochs, batch size=1, LR multiplier=2 are the settings we utilized)
- Combined AMT Parts 1+2 for relation classification (extended to 3-class task) -- you shouldn't need to use these, we recommend deploying ModernBERT. 

## Performance

| Task | Model | F1 Score | Notes |
|------|-------|----------|-------|
| AAEC Literal Extraction | GPT-4.1 | 94.44 | SOTA on published split |
| AAEC Literal Extraction | GPT-4.1-mini | 94.08 | Nearly matches GPT-4.1 |
| AMT Relation Classification | GPT-4.1 (FT) | 81.0 | 3-class task, Best we have been able to locate |
| AMT Relation Classification | ModernBERT-large | 79.0 | 500M params, dockerized, nearly 4.1|
| AMT Relation Classification | Claude Sonnet 4 (ICL) | 72.3 | 5-shot baseline  -- not implemented here|

## Example Outputs

The system generates interactive argument graphs showing:
- **Green edges**: Support relations
- **Red edges**: Attack relations  

## Citation

Paper currently under review. Preprint and citation information will be available soon. For now, please simply link to the repository. 

<!-- If you use this code in your research, please cite:

```bibtex
@inproceedings{cakar2026argument,
  title={The Argument is the Explanation: Structured Argumentation for Trust in Agents},
  author={Cakar, Ege and Kristensson, Per Ola},
  booktitle={Innovative Applications of Artificial Intelligence (IAAI)},
  year={2026}
}
``` -->

## API Requirements

- OpenAI API key (for GPT-4.1 models)
- Optional: RunPod API key (for cloud GPU deployment)

## Hardware Requirements

- **Minimum**: 16GB RAM, 4 CPU cores
- **Recommended**: 32GB RAM, 8 CPU cores, NVIDIA GPU (for local ModernBERT)

## License

MIT License - see LICENSE file for details

## Acknowledgments

This work was supported by the Department of Engineering, University of Cambridge, Trinity College, Cambridge and Harvard University, Harvard-Cambridge Summer Fellowship.

## Contact

Ege Cakar - ecakar@college.harvard.edu

Project Link: [https://github.com/Ege-Cakar/Structured-Argumentation-For-Trust](https://github.com/Ege-Cakar/Structured-Argumentation-For-Trust)
