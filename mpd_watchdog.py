#!/usr/bin/env python3
import os
import errno
import time
import pdb
from mpd import MPDClient, ConnectionError
from time import sleep
from subprocess import call

io = os.open("/tmp/mpd_watchdog", os.O_RDONLY | os.O_NONBLOCK)
last_recv = time.time()
mpd_client = MPDClient()

def mpd_connect():
	try:
		mpd_client.connect("localhost", 6600)
	except ConnectionError as err:
		pass
	except Exception:
		pdb.set_trace() # most likely something i did not think about died (e.g. timeout foo)


while True:
	try:
		buffer = os.read(io, 1024)
		buffer_filled = False
		for byte in buffer:
			buffer_filled |= byte
	except OSError as err:
		if err.errno == errno.EAGAIN or err.errno == errno.EWOULDBLOCK: # buffer empty
			buffer = None
		else:
			raise  # something else has happened -- better reraise

	if not buffer_filled and last_recv + 2 <= time.time(): # give the socket 2 seconds time before checking the mpd status
		print("buffer only nulls")
		mpd_connect()
		# TODO: back off (reduce retries) until mpd is available again

		status = mpd_client.status()
		if status["state"] == "play":
			# mpd is playing but no data flowing? Quick, recover!
			print("stall detected, resetting")
			try:
				mpd_client.stop()
				mpd_client.play()
			except BrokenPipeError:
				mpd_connect()
			else:
				last_recv = time.time()
			# TODO: make this smarter and escalate after some tries and restart mpd
			# call(["/etc/init.d/mpd", "restart"]) # a really hard way

		elif status["state"] == "pause" or status["state"] == "stop":
			last_recv = time.time()
			print("No data for over 5 seconds but MPD is in expected state \"{}\"".format(status["state"]))
			# TODO: stall/idle until MPD awakes again to avoid looping to much
			sleep(0.5) # for now we just sleep

	if buffer_filled:
		# everything is good
		last_recv = time.time()
		pass
