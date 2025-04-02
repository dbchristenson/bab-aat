def get_bbox(result):
    return result[0][0]

def get_ocr(result):
    return result[0][1][0]

def get_confidence(result):
    return result[0][1][1]