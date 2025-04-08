# What have we done
1. Experimented with OCR libraries to confirm that Olombendo documents cannot be read with simple methods
2. Converted olombendo PDFs to high-res images for training and analysis and organized naming to maintain linkage between pages for each document
3. Set up virtual machine on Google Cloud and transferred files to allow the use of "DarkMark" tool which assists in creating good data and evaluating computer vision networks. Also gives more graphical power than I have access to locally

# Future steps for tagging project

1. **Annotate more images from Olombendo to train the network**
2. **Pre-OCR Experimentation**
    - When using the network on PDFs it has not seen before, does it obtain the correct number of tags?
    - We can use the network on manually tagged documents to compare the # of tags a human notes v.s. the network
    - What accuracy % are we looking for to deem the network viable for the rest of the project?
3. **OCR Extraction**
    - The network identifies groupings of characters as tags and outlines them
    - Using the outlines, we cut out the image for OCR and hope that the quality of the document is high enough such that the OCR software makes no mistakes
    - If OCR still isn't enough, we may algorithmically upscale [the resolution of] either the entire image before processing or upscale the image of each tag to make characters more legible
4. **Data Organization**
    - When OCR extraction is acceptable, we organize the extracted data in a way that is agreeable to Bumi's current database
    - It would be good to do this for olombendo to start so I know how the pipelines for the other assets need to turn out
