"""使用marker将pdf转换为markdown

大文件出错；不用大模型时质量跟acrobat转HTML再转md差不多；
"""
import sys
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from marker.config.parser import ConfigParser

config = {
    "output_format": "markdown",
    # "ADDITIONAL_KEY": "VALUE"
}

config_parser = ConfigParser(config)

converter = PdfConverter(
    artifact_dict=create_model_dict(),
    config=config_parser.generate_config_dict(),
    processor_list=config_parser.get_processors(),
    renderer=config_parser.get_renderer(),
    # llm_service=config_parser.get_llm_service(),
)

if len(sys.argv) != 3:
    print("Usage: python pdf2md.py <input_pdf_path> <output_md_path>")
    sys.exit(1)

input_pdf_path = sys.argv[1]
output_md_path = sys.argv[2]

rendered = converter(input_pdf_path)
text, _, images = text_from_rendered(rendered)

with open(output_md_path, "w", encoding="utf-8") as f:
    f.write(text)
