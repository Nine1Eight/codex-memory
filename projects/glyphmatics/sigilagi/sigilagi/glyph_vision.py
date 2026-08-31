#!/usr/bin/env python3
import cv2
import pytesseract
import re

def extract_text(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return pytesseract.image_to_string(gray)

def extract_entities(text):
    return list(set(re.findall(r'\b[A-Z][a-zA-Z]+\b', text)))

def extract_numbers(text):
    return re.findall(r'\d+', text)

def extract_relations(text):
    relations = []
    if "arrive" in text.lower():
        relations.append({"s":"train","r":"arrive","o":"time"})
    if "leave" in text.lower():
        relations.append({"s":"train","r":"depart","o":"time"})
    return relations

def image_to_T(image_path):
    text = extract_text(image_path)

    T = {
        "E": extract_entities(text),
        "N": [{"v": int(n), "raw": n} for n in extract_numbers(text)],
        "R": extract_relations(text),
        "C": [],
        "T": [],
        "Q": [{"v": text}],
        "P": [{"src":"image"}]
    }

    return T, text

if __name__ == "__main__":
    import sys, json
    T, raw = image_to_T(sys.argv[1])
    print(json.dumps({"raw": raw, "T": T}, indent=2))
