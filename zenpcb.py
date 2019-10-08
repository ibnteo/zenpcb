#!/usr/bin/env python3
#coding: utf-8
# Version: 0.1 (beta)
# Date: 2019-10-09
# Author: Vladimir Romanovich <ibnteo@gmail.com>

import sys
import os
import zipfile

class ZenPCB:
	name = ''
	filenames = {
		'TopLayer': '.GTL',
		'BottomLayer': '.GBL',
		'Drills': '.XLN',
		'TopSilkscreen':'.GTO',
		'BottomSilkscreen':'.GBO',
		'BoardOutline':'.GKO',
		'TopSoldermask':'.GTS',
		'BottomSoldermask':'.GBS',
	}
	layers = {}

	def __init__(self, name='example'):
		self.name = name
		for key, value in self.filenames.items():
			self.filenames[key] = name + value

	# Создание Gerber-слоя
	def layer(self, layer=None, apertures={}):
		if self.layers.get(layer) is None:
			self.layers[layer] = ZenPCBLayer(apertures)
		return self.layers[layer]

	# Создание Exclellon-слоя для сверления
	def drill(self, layer=None, apertures={}):
		if self.layers.get(layer) is None:
			self.layers[layer] = ZenPCBDrill(apertures)
		return self.layers[layer]

	# Сохранить файлы проекта в директорию gerber/ и упаковать их в zip-архив
	def save(self):
		dir = 'gerber'
		if not os.path.exists(dir + '/'):
			os.mkdir(dir)
		os.chdir(dir)
		zip = zipfile.ZipFile(self.name + '.zip', 'w', zipfile.ZIP_DEFLATED)
		for name, l in self.layers.items():
			f = open(self.filenames[name], 'w')
			f.write(l.header)
			for key, val in l.buffer.items():
				f.write(val)
			f.write(l.footer)
			f.close()
			zip.write(self.filenames[name])
			print(dir + '/' + self.filenames[name] + ' saved')
		zip.close()
		os.chdir('..')
		print(dir + '/' + self.name + '.zip' + ' saved')

# Gerber
class ZenPCBLayer:
	header = '\n'.join(['%MOIN*%', '%FSLAX34Y34*%', '%IPPOS*%', 'G71*', 'G90*', ''])
	footer = 'M02*\n'
	x = 0
	y = 0
	baperture = None
	buffer = None

	def __init__(self, apertures={}):
		self.buffer = {}
		for key, val in apertures.items():
			if self.baperture is None:
				self.baperture = key
			#self.header = self.header + '%ADD' + key + 'C,' + '{:.4f}'.format(val) + '*%\n'
			self.header = self.header + '%ADD' + key + val + '*%\n'

	# Переключить апертуру
	def aperture(self, aperture='10'):
		self.baperture = aperture
		if self.buffer.get(self.baperture) is None:
			self.buffer[self.baperture] = 'G54D' + self.baperture + '*\n'
		return self

	# Выполнить операцию с перемещением апертуры
	def __draw(self, x, y, absolute, type):
		if absolute:
			self.x = x
			self.y = y
		else:
			self.x = self.x + x
			self.y = self.y + y
		if self.buffer.get(self.baperture) is None:
			self.buffer[self.baperture] = 'G54D' + self.baperture + '*\n'
		self.buffer[self.baperture] = self.buffer[self.baperture] + 'G01X' + '{:.4f}'.format(self.x).replace('.', '') + 'Y' + '{:.4f}'.format(self.y).replace('.', '') + type + '*\n'
	
	# Переместить без засветки
	def move(self, x, y, absolute=True):
		self.__draw(x, y, absolute, 'D02')
		return self

	# Перемещать с включённым светом
	def draw(self, x, y, absolute=True):
		self.__draw(x, y, absolute, 'D01')
		return self

	# Переместить без света и засветить апертурой данную точку
	def light(self, x, y, absolute=True):
		self.__draw(x, y, absolute, 'D03')
		return self

	# Обойти препятствие при движении слева-направо или снизу-вверх
	def bypass(self, x, y, r1, r2, side):
		sign = -1 if side == 'left' or side == 'down' else 1
		step = sign*r2
		if side == 'left' or side == 'right':
			if y-r1*1.5 > self.y:
				self.draw(x, y-r1*1.5)
			self.draw(step, r1, False).draw(0, r1, False).draw(-step, r1, False)
		else:
			if x-r1*1.5 > self.x:
				self.draw(x-r1*1.5, y)
			self.draw(x-r1*1.5+r1, y+step).draw(r1, 0, False).draw(r1, -step, False)
		return self

	# Нарисовать дугу в 1/4 круга по часовой стрелке
	def arc(self, x, y, absolute=True):
		if self.buffer.get(self.baperture) is None:
			self.buffer[self.baperture] = 'G54D' + self.baperture + '*\n'
		if not absolute:
			x = self.x + x
			y = self.y + y
		i, j = 0, 0
		if x < self.x and y < self.y:
			i = self.x - x
		if x > self.x and y > self.y:
			i = x - self.x
		if x > self.x and y < self.y:
			j = self.y - y
		if x < self.x and y > self.y:
			j = y - self.y
		self.buffer[self.baperture] = self.buffer[self.baperture] + 'G02X' + '{:.4f}'.format(x).replace('.', '') + 'Y' + '{:.4f}'.format(y).replace('.', '') + 'I' + '{:.4f}'.format(i).replace('.', '') + 'J' + '{:.4f}'.format(j).replace('.', '') + 'D01*\n'
		self.x = x
		self.y = y
		return self

	# Нарисовать круг дугами	
	def circle(self, r):
		if self.buffer.get(self.baperture) is None:
			self.buffer[self.baperture] = 'G54D' + self.baperture + '*\n'
		self.move(0, r, False).arc(r, -r, False).arc(-r, -r, False).arc(-r, r, False).arc(r, r, False).move(0, -r, False)
		return self

# Drill Excellon-2
class ZenPCBDrill:
	header = '\n'.join(['M48', 'METRIC,TZ', 'FMAT,2', 'ICI,OFF', ''])
	footer = 'M30\n'
	x = 0
	y = 0
	baperture = None
	buffer = None

	def __init__(self, apertures={}):
		self.buffer = {}
		for key, val in apertures.items():
			if self.baperture is None:
				self.baperture = key
			#self.header = self.header + 'T' + key + 'C' + '{:.4f}'.format(val) + '\n'
			self.header = self.header + 'T' + key + val + '\n'
		self.header = self.header + '%' + '\n'

	# Сменить апертуру (сверло)
	def aperture(self, aperture='01'):
		self.baperture = aperture
		if self.buffer.get(self.baperture) is None:
			self.buffer[self.baperture] = 'T' + self.baperture + '\n'
		return self

	# Переместить курсор
	def move(self, x, y, absolute=True):
		if absolute:
			self.x = x
			self.y = y
		else:
			self.x = self.x + x
			self.y = self.y + y
		return self

	# Просверлить отверстие
	def drill(self, x, y, absolute=True):
		if absolute:
			self.x = x
			self.y = y
		else:
			self.x = self.x + x
			self.y = self.y + y
		if self.buffer.get(self.baperture) is None:
			self.buffer[self.baperture] = 'T' + self.baperture + '\n'
		self.buffer[self.baperture] = self.buffer[self.baperture] + 'X' + '{:.4f}'.format(self.x) + 'Y' + '{:.4f}'.format(self.y) + '\n'
		return self
