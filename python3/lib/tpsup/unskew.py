from PIL import Image
import pytesseract
import cv2
import numpy as np

# Load the image
image_path = '/mnt/data/mmexport1736192781088.jpg'
image = cv2.imread(image_path)

# Convert to grayscale
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Detect edges
edges = cv2.Canny(gray, 50, 150)

# Find contours
contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contours = sorted(contours, key=cv2.contourArea, reverse=True)

# Assume the largest contour is the document
doc_contour = contours[0]

# Approximate the contour to a quadrilateral
epsilon = 0.02 * cv2.arcLength(doc_contour, True)
approx = cv2.approxPolyDP(doc_contour, epsilon, True)

# If a quadrilateral is detected, proceed with perspective transformation
if len(approx) == 4:
    # Reorder points to ensure consistency
    def order_points(pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    # Get ordered points
    pts = approx.reshape(4, 2)
    rect = order_points(pts)
    
    # Compute width and height of the new image
    (tl, tr, br, bl) = rect
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    # Perspective transformation matrix
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

    # Save the corrected image
    corrected_path = "/mnt/data/corrected_document.jpg"
    cv2.imwrite(corrected_path, warped)
    corrected_path
else:
    "Failed to detect a quadrilateral document."
