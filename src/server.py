# WAIVE-FRONT Archive Tools
# Copyright (C) 2024  Bram Bogaerts, Superposition

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from PIL import Image
from transformers import AutoModelForCausalLM
from transformers import AutoProcessor
from transformers import BitsAndBytesConfig
import torch

import time

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO

allowed_tags = ["Transportation", "Mechanical", "Small", "Static", "Movement", "Audio", "Large", "Weather", "Industrial", "Communication", "Light", "Everyday", "Atmospheric", "Commercial", "Urban", "Visual", "Geographical", "Night", "Day", "Electronic", "Interior", "Sporting", "Social", "Public", "Historical", "Heavy", "Domestic", "Educational", "Animal", "Human", "Cultural", "Recreational", "Linguistic", "Technology", "Rural", "Natural", "Agricultural", "Exterior", "Occupational", "Medical", "Modern", "Seasonal", "Event"]
allowed_tags_lower = [tag.lower() for tag in allowed_tags]

model_id = "microsoft/Phi-3-vision-128k-instruct"

processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)

nf4_config = BitsAndBytesConfig(
	load_in_4bit=True,
	bnb_4bit_quant_type="nf4",
	bnb_4bit_use_double_quant=True,
	bnb_4bit_compute_dtype=torch.bfloat16,
)

model = AutoModelForCausalLM.from_pretrained(
	model_id,
	device_map="cuda",
	trust_remote_code=True,
	torch_dtype="auto",
	quantization_config=nf4_config,
)

def tag(data, raw_mode=False, prompt="Give me five words that describe this image. Format your response as a comma-separated list of words."):
	start_time = time.time()

	message = [{"role": "user", "content": "<|image_1|>" + prompt}]
	
	prompt = processor.tokenizer.apply_chat_template(
		message, tokenize=False, add_generation_prompt=True
	)

	image = None

	if raw_mode:
		image = Image.open(BytesIO(data))
	else:
		image = Image.open(data)

	inputs = processor(prompt, [image], return_tensors="pt").to("cuda:0")

	generate_ids = model.generate(
		**inputs,
		eos_token_id=processor.tokenizer.eos_token_id,
		max_new_tokens=500,
		do_sample=False
	)

	generate_ids = generate_ids[:, inputs["input_ids"].shape[-1] :]

	response = processor.batch_decode(
		generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False
	)[0]

	end_time = time.time()

	response_parsed = response.lower()
	response_parsed = "".join([c for c in response_parsed if c.isalpha() or c == " "])
	response_parsed = response_parsed.split(" ")
	
	found_tags = [tag for tag in response_parsed if tag in allowed_tags_lower]
	found_tag = found_tags[0] if len(found_tags) > 0 else None

	return {"tag": found_tag, "response": response, "time_taken": end_time - start_time}


class RequestHandler(BaseHTTPRequestHandler):
	def do_POST(self):
		content_length = int(self.headers["Content-Length"])
		image = self.rfile.read(content_length)

		try:
			response = tag(image, raw_mode=True, prompt="From the following list, which category fits this image?\n\n" + ", ".join(allowed_tags) + ".\nExplain your choice.")
			self.send_response(200)
			self.send_header("Content-type", "application/json")
			self.end_headers()
			self.wfile.write(json.dumps(response).encode("utf-8"))
		except Exception as e:
			response = {"error": str(e)}
			self.send_response(500)
			self.send_header("Content-type", "application/json")
			self.end_headers()
			self.wfile.write(json.dumps(response).encode("utf-8"))

server = HTTPServer(("0.0.0.0", 8080), RequestHandler)
server.serve_forever()

# usage:
#  curl -X POST -d @example.png http://192.168.128.101:8080
