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

import os
import tqdm
import uuid
import csv
import requests
import json

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Video:
	def __init__(self, filename, sourceID, title, source, tags):
		self.filename = filename
		self.title = title
		self.source = source
		self.tags = tags
		self.id = uuid.uuid4().hex
		self.sourceID = sourceID
		self.shots = []
	
class Shot:
	def __init__(self, start, end, duration, video, id, itemPath, previewPath):
		self.start = start
		self.end = end
		self.duration = duration
		self.video = video
		self.id = id
		self.itemPath = itemPath
		self.previewPath = previewPath
		self.category = ""
		self.tags = []
		
		self.video.shots.append(self)

source = ""
ip = ""
inputPath = ""
outputPath = ""
videoList = []
existingIDs = []
outJSON = {}

def readCSV(filename):
	with open(filename, mode='r') as file:
		csvFile = csv.reader(file)
		# skip the header

		for i, row in enumerate(csvFile):
			if i == 0:
				continue

			id = row[1]

			if id in existingIDs:
				continue

			videoList.append(Video(row[0], row[1], row[2], row[3], row[4]))

def splitVideo(video):
	shotList = []

	_in = inputPath + "/video/" + video.filename
	_out = "output/" + source + "/items/" + video.id + ".mp4"
	_preview = "output/" + source + "/___tmp/" + video.id + ".png"

	command = "ffprobe -loglevel error -skip_frame nokey -select_streams v:0 -show_frames -of compact=p=0 -f lavfi \"movie=" + _in + ",select=gt(scene\\,0.5)\""
	result = os.popen(command).read().split("\n")

	shots = [{"start": 0}]

	for line in result:
		data = line.split("|")
		for d in data:
			spl = d.split("=")

			if len(spl) < 2:
				continue

			key = spl[0]
			value = spl[1]

			if key == "pkt_pts_time":
				shots[-1]["end"] = float(value)
				shots[-1]["duration"] = shots[-1]["end"] - shots[-1]["start"]
				shots.append({"start": float(value)})

	shots.pop()

	shots = [shot for shot in shots if shot["duration"] > 2]

	for shot in shots:
		if shot["duration"] > 10:
			shot["duration"] = 10
			shot["end"] = shot["start"] + 10

	for i, shot in enumerate(shots):
		start = shot["start"]
		duration = shot["duration"]

		command = "ffmpeg -loglevel error -ss " + str(start) + " -i " + _in + " -t " + str(duration) + " -c copy " + _out.replace(".mp4", "-" + str(i) + ".mp4")
		os.system(command)

		middle = start + duration / 2
		command = "ffmpeg -loglevel error -ss " + str(middle) + " -i " + _in + " -vframes 1 -q:v 2 " + _preview.replace(".png", "-" + str(i) + ".png")
		os.system(command)

		shotList.append(Shot(start, start + duration, duration, video, i, _out.replace(".mp4", "-" + str(i) + ".mp4"), _preview.replace(".png", "-" + str(i) + ".png")))

	return shotList

def processShot(shot):
	with open(shot.previewPath, "rb") as file:
		response = requests.post("http://" + ip, data=file)

		if response.status_code == 200:
			data = response.json()
			tag = data["tag"]

			shot.category = tag

def processVideo(video):
	if not os.path.exists("output/" + source + "/___tmp"):
		os.makedirs("output/" + source + "/___tmp")
		
	shots = splitVideo(video)
	t = tqdm.tqdm(shots)
	t.set_description(f"Processing {len(shots)} shots from {video.filename}")

	for shot in t:
		processShot(shot)

		outJSON["items"].append({
			"id": video.id,
			"sceneID": shot.id,
			"originalID": video.sourceID,
			"title": video.title,
			"source": video.source,
			"tags": video.tags.split("|"),
			"category": shot.category,
		})

		with open("output/" + source + "/data.json", "w") as file:
			json.dump(outJSON, file, indent=4, sort_keys=True, separators=(',', ': '))

	os.system("rm -rf output/" + source + "/___tmp")

def main():
	global bgcolors

	if len(os.sys.argv) < 3:
		print(bcolors.OKBLUE);
		print("Usage: python main.py path-to-source-directory ip-address-of-server")
		print();
		print("Example directory structure:")
		print();
		print("└─┬─ name-of-source")
		print("  ├─┬─ video")
		print("  │ ├─── example-1.mp4")
		print("  │ └─── example-2.mp4")
		print("  └─── data.csv")
		print();
		print("data.csv example:")
		print();
		print("filename,      title,           source,   tags")
		print("example-1.mp4, Title of item 1, Source A, tag1|tag2|tag3")
		print("example-2.mp4, Title of item 2, Source A, tag4|tag2|tag5")
		print(bcolors.ENDC);
		exit()
	
	path = os.sys.argv[1]

	global ip
	ip = os.sys.argv[2] + ":8080"

	if not os.path.exists(path):
		print(bgcolors.FAIL + "The path does not exist." + bcolors.ENDC)
		exit()

	if not os.path.exists(path + "/data.csv"):
		print(bcolors.FAIL + "The data.csv file does not exist." + bcolors.ENDC)
		exit()

	if not os.path.exists(path + "/video"):
		print(bcolors.FAIL + "The video folder does not exist." + bcolors.ENDC)
		exit()

	global source
	source = os.path.basename(path).lower().replace(" ", "_").replace("-", "_").replace(".", "_")

	global outJSON
	global existingIDs

	if os.path.exists("output/" + source + "/data.json"):
		with open("output/" + source + "/data.json", "r") as file:
			outJSON = json.load(file)

		for video in outJSON["items"]:
			if video["originalID"] not in existingIDs:
				existingIDs.append(video["originalID"])

		print(bcolors.OKGREEN + "Loaded existing data.json file." + bcolors.ENDC)
	else:
		outJSON = {"source": source, "items": []}
		print(bcolors.OKGREEN + "Created new data.json file." + bcolors.ENDC)

	readCSV(path + "/data.csv")

	for video in videoList:
		if video.filename.endswith(".mp4"):
			if not os.path.exists(path + "/video/" + video.filename):
				print(bcolors.FAIL + "The video file: " + video.filename + " does not exist in the video folder." + bcolors.ENDC)
				exit()

	if not os.path.exists("output/" + source + "/items"):
		os.makedirs("output/" + source + "/items")
		print(bcolors.OKGREEN + "Created output folder." + bcolors.ENDC)

	global inputPath
	global outputPath
	inputPath = path
	outputPath = "output/" + source

	t = tqdm.tqdm(videoList)
	t.set_description(f"Processing {len(videoList)} videos")

	for video in t:
		processVideo(video)

if __name__ == "__main__":
	main()
