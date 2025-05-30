# BAB OCR API Documentation

Welcome to the Bumi Armada OCR API system for document processing and optical character recognition.

## Table of Contents

## Overview

The BAB OCR API is a comprehensive document processing system that enables:

- **Document Upload**: Support for PDF files and ZIP archives
- **OCR Processing**: Configurable optical character recognition
- **Batch Operations**: Process multiple documents by vessel and department
- **Visual Results**: Annotated images with detected text regions
- **Export Capabilities**: Extract and export processed data

## Getting Started

### 1. Upload Documents

Navigate to the [Upload](/ocr/upload) page to submit your documents:

- **Supported formats**: PDF files, ZIP archives containing PDFs
- **Maximum size**: 2.5GB per upload
- **Organization**: Documents are organized by vessel

### 2. Create OCR Configuration

Before processing, create an OCR configuration:

1. Go to [OCR Config](/ocr/configs/create/)
2. Specify model parameters
3. Set processing scale and confidence thresholds

### 3. Run Detection

Process your documents using the [Detection](/ocr/documents/detect/by_origin/) interface:

- Select vessel and department origin
- Choose your OCR configuration
- Monitor processing status

### 4. View Results

Check processed documents in the [Documents](/ocr/documents/) section:

- Browse uploaded documents
- View OCR results and annotations
- Export detected text data

## Features

### Document Processing

The system supports robust document processing with:

```python
# Example OCR configuration
{
    "paddle": {
        "use_angle_cls": true,
        "lang": "en",
        "det_model_dir": "en_PP-OCRv3_det_infer",
        "rec_model_dir": "en_PP-OCRv4_rec_infer"
    },
    "scale": 4.0,
    "min_confidence": 0.6
}
```

### Batch Processing

Process multiple documents efficiently:

- **By Vessel**: Process all documents for a specific vessel
- **By Department**: Filter by department origin
- **Configurable**: Use different OCR models per batch

### Visual Annotations

The system provides visual feedback:

- Bounding boxes around detected text
- Color-coded confidence levels
- Exportable annotated images

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ocr/upload/` | POST | Upload documents |
| `/ocr/documents/` | GET | List documents |
| `/ocr/documents/{id}/` | GET | Document details |
| `/ocr/documents/{id}/get_detections/` | POST | Run OCR |
| `/ocr/configs/create/` | POST | Create config |

## Configuration

### OCR Models

The system supports various PaddleOCR models:

- **English**: `en_PP-OCRv3_det_infer`, `en_PP-OCRv4_rec_infer`
- **Chinese**: `ch_PP-OCRv3_det_infer`, `ch_PP-OCRv4_rec_infer`
- **Multilingual**: `multilingual_PP-OCRv3_det_infer`

### Processing Parameters

Key configuration options:

- **Scale**: Image upscaling factor (1.0-8.0)
- **Confidence**: Minimum detection confidence (0.0-1.0)
- **Angle Classification**: Enable text angle detection
- **Binary**: Use binary image processing

## Memory Management

The system includes advanced memory monitoring and management:

- **Real-time tracking**: Monitor memory usage during processing
- **Automatic cleanup**: Aggressive garbage collection to prevent leaks
- **Threshold monitoring**: Automatic intervention when memory usage is high
- **Process isolation**: Each document processed in isolated memory contexts

## Troubleshooting

### Common Issues

**Memory Errors**
> If you encounter out-of-memory errors, try reducing the scale parameter or processing smaller batches.

**Low Detection Accuracy**
> Adjust the confidence threshold and ensure good image quality. Consider using angle classification for rotated text.

**Slow Processing**
> Large scale factors increase processing time. Balance between accuracy and speed based on your needs.

### Support

For technical support or questions:

- Check the [Documents](/ocr/documents/) page for processing status
- Review OCR configurations for parameter issues
- Monitor system resources during batch processing

## System Requirements

### Hardware
- **RAM**: Minimum 8GB, recommended 16GB+
- **Storage**: SSD recommended for faster processing
- **CPU**: Multi-core processor recommended

### Software
- **Python**: 3.8+
- **Django**: 4.x
- **PaddleOCR**: Latest version
- **Redis**: For task queuing
- **PostgreSQL**: Database backend

## Development

### Setup
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure database settings
4. Run migrations: `python manage.py migrate`
5. Start services: `docker-compose up`

### Testing
```bash
# Run tests
python manage.py test

# Test memory monitoring
python manage.py shell -c "from ocr.main.utils.memory import MemoryMonitor; m = MemoryMonitor('test'); print('Memory monitoring working!')"
```

---

*Last updated: System automatically updates documentation based on current configuration*