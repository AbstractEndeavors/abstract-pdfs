from time import time
import setuptools
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
setuptools.setup(
    name='abstract_pdfs',
    version='0.0.37',
    author='putkoff',
    author_email='partners@abstractendeavors.com',
    description='A structured pipeline for transforming PDFs into **searchable, metadata-rich, web-ready content**, combining OCR, page-level analysis, metadata generation, and static site scaffolding.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/AbstractEndeavors/abstract_pdfs',
    classifiers=[
      'Development Status :: 3 - Alpha',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: MIT License',
      'Programming Language :: Python :: 3',
      'Programming Language :: Python :: 3.11',
    ],
    install_requires=[
        'abstract_ocr',
        'abstract_utilities',
        'pymupdf',
        'PyMuPDF',
        'SpeechRecognition',
        'keybert',
        'whisper',
        
        ]
,
   package_dir={"": "src"},
   packages=setuptools.find_packages(where="src"),
   python_requires=">=3.6",
  

)
