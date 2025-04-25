import os, json, re
from collections import defaultdict
import copy
import random
random.seed(34)
import traceback

class Eval(object):
	def __init__(self):
		self.llm = 'qwen2.5_32b'
		self.llm = 'qwen2.5_7b_lora'
		# self.llm = 'qwen2.5_7b'
		self.llm = 'qwen2.5_14b'
		# self.llm = 'qwen2.5_14b_lora'
		# self.llm = 'qwen2.5_14b_lora_1_3_new'
		# self.llm = 'qwen2.5_14b_lora_1_3_filter'
		# self.llm = 'ds_qwen2.5_14b'
		self.tp, self.fp, self.fn, self.tn = 0,0,0,0   #分类型时的计数
		self.total_tp, self.total_fp, self.total_fn, self.total_tn = 0,0,0,0
		#tp: 实际为正，预测也为正
		#tn: 实际为负，预测也为负
		#fp: 实际为负，但预测为正
		#fn: 实际为正，但预测为负
		self.toge = True   #所有类型的错误一起统计
		# self.toge = False
		self.error_types = ["常识性错误", "数值单位错误", "时间矛盾错误", "数据重复错误", "逻辑矛盾错误", "数值前后不一致", "数据缺失错误", "计算错误"]
		self.error_types = ["数值缺失错误", "语句缺失错误" ,
							"格式错误", "时间信息非法", "数值单位错误", 
							"冗余语句", "时间矛盾错误", "计算错误", "语义逻辑矛盾", "数值不一致错误"]

		self.current_error = ''					
		self.scores = {}

	def handle_llm_output(self, output):
		pattern = r'\[\"(.*)\"\]'
		pa = r'[^\\]\\[^\\"]'
		pa1 = r'[^\"]\"\"[^\"\]]'
		res = []   #返回的嵌套列表
		sentences = output.split('\n')

		for text in sentences:
			try:
				if text:
					temp_res = re.search(pattern, text)
					if temp_res: 
						temp_res = temp_res.group()
						# print('-----------\ntemp_res:', temp_res)
						if '"，"' in temp_res:
							temp_res = temp_res.replace('"，"', '", "')

						if re.search(pa, temp_res):
							temp_res = temp_res.replace('\\', '\\\\')
						if re.search(pa1, temp_res):
							temp_res = temp_res.replace('""', '"')
						temp_res = json.loads(temp_res)
						if isinstance(temp_res, list):
							if len(temp_res) == 1 and temp_res[0] == "":
								pass 
							elif len(temp_res) == 2 and temp_res[0] == temp_res[1]:
								res.append([temp_res[0]])
							else:
								res.append(temp_res)
						else:
							print('warn temp_res 类型不对', type(temp_res), temp_res)
			except:
				print("output:", output)
				print("text:", text)

				traceback.print_exc()
				continue
			
		return res
	
	def new_handle_llm_output_nest(self, output):
		#处理的是单维列表中存储的不是冲突的文本对
		if  '</think>' in output:
			output = output.split('</think>')[1]
		output = re.sub(r'\n(\s*)', '', output)	
		output = output.replace('\n    ', '').replace(']\n]',']]').replace('　', ' ').replace('[\n[', '[[')
		
		pattern = r'\[([^\]]*?)\]'    #只抽取[]里面的内容

		pa = r'"(.*?)"'
		res = []   #返回的嵌套列表
		# sentences = output.split('\n')
		sentences = re.split(r'[。，]\n', output)

		mid_res = []
		for text in sentences[::-1]:
			try:
				if text:
					text = text.replace('\n    ', '').replace(']\n]',']]').replace('[\n[', '[[').replace('"，"', '", "')
					temp_res = re.findall(pattern, text)
					if temp_res:
						for x in temp_res:
							temp_x = re.findall(pa, x)
							if temp_x:
								for y in temp_x:
									if not y:
										continue
									mid_res.append([y])

				for temp_y in mid_res:
					flag = False
					for i, temp_res in enumerate(res):
						for j in range(len(temp_res)):
							if temp_y[0] in temp_res[j]:
								flag = True
								break
							elif temp_res[j] in temp_y[0]:
								res[i][j] = temp_y[0]
								flag = True
								break
						if flag:
							break
					if not flag:
						res.append(temp_y)	
				if res:
					break
			except:
				print("output:", output)
				print("text:", text)
				print('temp_res:', temp_res)
				traceback.print_exc()
				continue

		print('-----------------------\n normal output: ', output)
		print(' normal res:', json.dumps(res, ensure_ascii=False))	
		print('-----------------')	
		return res

	def new_handle_llm_output(self, output):
		#处理的是单维列表中存储的冲突的文本对
		if  '</think>' in output:
			output = output.split('</think>')[1]
		output = re.sub(r'\n(\s*)', '', output)	
		output = output.replace('\n    ', '').replace(']\n]',']]').replace('　', ' ').replace('[\n[', '[[')
		
		pattern = r'\[([^\]]*?)\]'    #只抽取[]里面的内容

		# pa = r'[^\\]\\[^\\"]'
		# pa1 = r'[^\"]\"\"[^\"\]]'
		pa = r'"(.*?)"'
		res = []   #返回的嵌套列表
		sentences = output.split('\n')

		for text in sentences[::-1]:
			try:
				if text:
					text = text.replace('\n    ', '').replace(']\n]',']]').replace('[\n[', '[[').replace('"，"', '", "')
					temp_res = re.findall(pattern, text)
					if temp_res:
						for x in temp_res:
							temp_y = []
							temp_x = re.findall(pa, x)
							if temp_x:
								for y in temp_x:
									temp_y.append(y)

									
							if len(temp_y) > 2:
								print('最多只能输出一对sentences', temp_y, text,  output)
							else:
								flag = False
								if len(temp_y) ==2:
									if temp_y[0] in temp_y[1]:
										temp_y = [temp_y[1]]
										flag = True
									elif temp_y[1] in temp_y[0]:
										temp_y = [temp_y[0]]
										flag = True
								elif len(temp_y) == 1:
									for i, temp_res in enumerate(res):
										for j in range(len(temp_res)):
											if temp_res[j] in temp_y[0]:
												res[i][j] = temp_y[0]
												flag = True
												break
											elif temp_y[0] in temp_res[j]:
												flag = True
												break
										if flag:
											break
								if not flag and temp_y:
									res.append(temp_y)	
						break
				
			except:
				print("output:", output)
				print("text:", text)
				print('temp_res:', temp_res)
				traceback.print_exc()
				continue

		print('-----------------------\n normal output: ', output)
		print(' normal res:', json.dumps(res, ensure_ascii=False))	
		print('-----------------')	
		return res

	def new_handle_llm_lora_output(self, output):
		try:
			output = output.split('<|answer_start|>')[-1].replace('<|answer_end|>', '').replace('\n', '')
			output = output.split('json')[-1].split('```')[0]
			# if not output.startswith('{'):
			# 	output = '{' +output.split('{')[-1]
			# output = output.split('}')[0]+'}'
			# try:
			# 	res = json.loads(output)
			# except:
			# 	traceback.print_exc()
			# 	print(output)
			pa = r'{"sentences{0,1}":\s*\[.*\]'
			res = re.findall(pa, output)
			if res:
				if '[[' in res[0] and ']' not in res[0]:
					res[0] = res[0].replace(']', ']]')
				# print('res:' , res[0]+'}')
				try:
					res = json.loads(res[0]+'}')
				except:
					traceback.print_exc()
					print('output:', output)
					print('res:', res)
					res = {}
			else:
				pa = r'{"sentences{0,1}":\s*\".*\"'
				res = re.findall(pa, output)
				if res:
					# print('res:' , res[0]+'}')
					try:
						res = json.loads(res[0]+'}')
					except:
						traceback.print_exc()
						print('output:', output)
						print('res:', res)
						res = {}
				else:
					pa = r'{"text":\s*\".*\"'
					res = re.findall(pa, output)
					if res:
						# print('res:' , res[0]+'}')
						try:
							res = json.loads(res[0]+'}')
						except:
							traceback.print_exc()
							print('output:', output)
							print('res:', res)
							res = {}
					else:
						print('未考虑到得情况', output)
						res = {}

			
			for k, v in res.items():
				if isinstance(v, str):
					res = [[v]]
				elif isinstance(v, list):
					if len(v) == 0:
						res = []
						break
					try:
						if isinstance(v[0], str):
							res = [v]
						elif isinstance(v[0], list):
							res = v
						else:
							print('warning 没有考虑到的情况', v)
					except:
						traceback.print_exc()
						print('内部出错,', v)
				else:
					print('warning 没有考虑到的情况', v)
				break

			print('-----------------------\n normal output: ', output)
			print(' normal res:', json.dumps(res, ensure_ascii=False))	
			print('-----------------')

		except:
			traceback.print_exc()
			print("output:", output)
			print('res:', res)
			res = []
		return res

	def old_handle_llm_output(self, output):
		output = output.replace('\n    ', '').replace(']\n]',']]').replace('　', ' ')
		pattern = r'\[\[\"(.*)\"\]{2,3}'    #嵌套列表

		pa = r'[^\\]\\[^\\"]'
		pa1 = r'[^\"]\"\"[^\"\]]'
		res = []   #返回的嵌套列表
		sentences = output.split('\n')

		for text in sentences:
			try:
				if text:
					temp_res = re.search(pattern, text)
					if temp_res: 
						temp_res = temp_res.group()
						# print('-----------\ntemp_res:', temp_res)
						if '"，"' in temp_res:
							temp_res = temp_res.replace('"，"', '", "')

						if re.search(pa, temp_res):
							temp_res = temp_res.replace('\\', '\\\\')
						if re.search(pa1, temp_res):
							temp_res = temp_res.replace('""', '"')
						temp_res = temp_res.replace('工阶段对建设工程质量、进度、造价进行控制……", 第2包、第3包表述重复，这里只是摘取一个代表', '工阶段对建设工程质量、进度、造价进行控制……"')
						temp_res = temp_res.replace('[["时间：5万个工作日"]]]', '[["时间：5万个工作日"]]')
						temp_res = temp_res.replace('["提交（上传）响应文件截止时间：""]', '["提交（上传）响应文件截止时间："]')
						temp_res = json.loads(temp_res)
						for x in temp_res:
							if isinstance(x, list):
								if len(x) == 1:
									if x[0] == "":
										pass 
									else:
										res.append(x)
								elif len(x) == 2:
									if x[0] == x[1]:
										res.append([x[0]])
									elif isinstance(x[0], str) and isinstance(x[1], str):
										res.append(x)
								else:
									print('最多只能输出一对sentences', x, output)
							else:
								print('warn temp_res 类型不对', type(x), x)
			except:
				print("output:", output)
				print("text:", text)
				print('temp_res:', temp_res)
				traceback.print_exc()
				continue

		return res

	def new_handle_file(self, file, all_outputs, logic):
		"""
		all_output: {"": [[]]}, 已得到的结果
		"""

		with open(file, 'r', encoding='utf-8') as fr:
			response = json.load(fr)
			for data in response:
				fname, output = data['name'], data['res']
				# if '中国地震局地质研究所园区综合物业管理服务采购项目招标公告' not in fname:
				# 	continue

				print('当前处理的文件是', fname)
				# print("output:", output)
				if 'lora' in self.llm:
					res = self.new_handle_llm_lora_output(output)
				else:
					if not logic:
						res = self.new_handle_llm_output_nest(output)
					else:
						res = self.new_handle_llm_output(output)
				if not res: 
					# print(f"fname: {fname}, output: {output}")
					# print('------------\n匹配结果：', res, '\n------------')
					all_outputs[fname] = []
					print('结束后的', all_outputs[fname])
				# print('output-------\n', output	)
				# print('res------------\n', res)

				for x in res:
					print('当前处理的错误的是', x)
					if not isinstance(x, list):
						continue
					flag = False
					if len(x) == 1:
						for i, y in enumerate(all_outputs[fname]):
							if len(y) == 1:
								if x[0] in y[0]:
									# print('新的结果被老的合并: old', y, 'new:', x)
									flag = True
									break
								elif y[0] in x[0]:
									all_outputs[fname][i] = x
									# print('多次预测的结果合并, 老的结果被新的合并: old', y, 'new:', x)
									flag = True
									break
							else:
								if (x[0] in y[0]) or (x[0] in y[1]):
									flag = True
									break
								elif y[0] in x[0]:
									flag = True
									all_outputs[fname][i][0] = x[0]
									break
								elif y[1] in x[0]:
									flag = True
									all_outputs[fname][i][1] = x[0]
									break

						if not flag:
							all_outputs[fname].append(x)
					
					elif len(x) == 2:
						old_len = len(all_outputs[fname])
						for j, y in enumerate(all_outputs[fname][::-1]):
							i = old_len - j -1 
							if len(y) == 1:
								if (y[0] in x[0]) or (y[0] in x[1]):
									print('删除之前单个语句', all_outputs[fname], i)
									del all_outputs[fname][i]
									continue
								elif (x[0] in y[0]) or (x[1] in y[0]):
									continue

							elif len(y) == 2:
								if x[0] in y[0]:
									if x[1] in y[1]:
										print('1 新的结果被老的合并: old', y, 'new:', x)
										flag = True
										break
									elif y[1] in x[1]:
										print('1 老的结果被新的合并: old', y, 'new:', x)
										all_outputs[fname][i][1] = x[1]
										flag = True
										break
								elif y[0] in x[0]:
									if x[1] in y[1]:
										print('2 新的结果被老的合并: old', y, 'new:', x)
										all_outputs[fname][i][0] = x[0]
										flag = True
										break
									elif y[1] in x[1]:
										print('2 老的结果被新的合并: old', y, 'new:', x)
										all_outputs[fname][i] = x
										flag = True
										break
								elif x[0] in y[1]:
									if x[1] in y[0]:
										print('3 新的结果被老的合并: old', y, 'new:', x)
										flag = True
										break
									elif y[0] in x[1]:
										print('3 老的结果被新的合并: old', y, 'new:', x)
										all_outputs[fname][i][0] = x[1]
										flag = True
										break
								elif y[1] in x[0]:
									if x[1] in y[0]:
										print('4 新的结果被老的合并: old', y, 'new:', x)
										all_outputs[fname][i][1] = x[0]
										flag = True
										break
									elif y[0] in x[1]:
										print('4 老的结果被新的合并: old', y, 'new:', x)
										all_outputs[fname][i] = x
										flag = True
										break
						if not flag:
							all_outputs[fname].append(x)
					print('结束后的', all_outputs[fname])
					
				#break

		return all_outputs

	def handle_file(self, file, all_outputs, logic):
		"""
		all_output: {"": [[]]}, 已得到的结果
		"""

		with open(file, 'r', encoding='utf-8') as fr:
			response = json.load(fr)
			for data in response:
				fname, output = data['name'], data['res']
				# if '中国地震局地质研究所园区综合物业管理服务采购项目招标公告' not in fname:
				# 	continue

				print('当前处理的文件是', fname)
				# print("output:", output)
				#res = self.handle_llm_output(output)
				res = self.new_handle_llm_output(output)
				if not res: 
					# print(f"fname: {fname}, output: {output}")
					# print('------------\n匹配结果：', res, '\n------------')
					pass
				print('output-------\n', output	)
				print('res------------\n', res)
				# if len(res) == 1:
				# 	if ('矛盾' in output or '不一致' in output) and isinstance(res[0], list) and len(res[0]) == 2:
				# 		all_outputs[fname].append(res[0])
				# 		return all_outputs

				for x in res:
					print('当前处理的错误的是', x)
					if len(x) == 1:
						flag = False
						for i, y in enumerate(all_outputs[fname]):
							if len(y) == 1:
								if x[0] in y[0]:
									# print('新的结果被老的合并: old', y, 'new:', x)
									flag = True
									continue
								elif y[0] in x[0]:
									all_outputs[fname][i] = x
									# print('多次预测的结果合并, 老的结果被新的合并: old', y, 'new:', x)
									flag = True
									break
						if not flag:
							all_outputs[fname].append(x)
					
					elif logic:
						if len(x) == 2:
							all_outputs[fname].append(x)
						else:
							print('warn 嵌套列表中最多只能有一对句子', x)

					else:
						for temp_x in x:
							flag = False
							for i, y in enumerate(all_outputs[fname]):
								if len(y) == 1:
									if temp_x in y[0]:
										print('新的结果被老的合并: old', y, 'new:', temp_x)
										flag = True
										continue
									elif y[0] in temp_x:
										all_outputs[fname][i] = temp_x
										print('多次预测的结果合并, 老的结果被新的合并: old', y, 'new:', temp_x)
										flag = True
										break
							if not flag:
								all_outputs[fname].append([temp_x])
					print('结束后的', all_outputs[fname])
					
				#break

		return all_outputs

	def compare(self, outputs, gd_sents, toge=False):
		"""
			outputs: {"":[]}
			gd_sents: {"": []}
			toge: 默认所有错误类型一起统计结果
		"""
		for fname, p_sents in outputs.items():
			print('-----------\n 当前处理的文件是:', fname)
			self.compare_single_doc(fname, p_sents, gd_sents.get(fname, []), toge)

		print(f"TP: {self.tp}, FP: {self.fp}, FN: {self.fn}")
		pre = round(self.tp *100 /max(self.tp +self.fp, 1), 2)
		rec = round(self.tp * 100 / max(self.tp + self.fn, 1), 2)
		if pre+rec == 0:
			f1 = round(2*pre*rec, 2)
		else:
			f1 = round(2*pre*rec/(pre+rec), 2)

		self.total_tp += self.tp
		self.total_fp += self.fp
		self.total_fn += self.fn

		if self.toge:
			# if len(gd_sents.get(fname, [])) == 0:
			# 	print( 'gd_sents' ,gd_sents.get(fname, []))
			print(f"num: {self.tp+self.fn},  Rec: {rec}")
		else:
			print(f"Pre: {pre}, Rec: {rec}, F1: {f1}")

		self.scores[self.current_error] = {'tp': self.tp, 'fp': self.fp, 'fn': self.fn,
											'pre': pre, 'rec': rec, 'f1': f1}

	def compare_single_doc(self, fname, p_sents, gd_sents, toge):
		sents_g_single = []   #单个句子错误
		sents_g_pair = []	#句子对错误
		for p in gd_sents:
			if len(p) == 2:
				sents_g_pair.append(p)
			elif len(p) == 1:
				sents_g_single.extend(p)
			else: 
				print(p, 'warn 未考虑到的数据格式')  
		
		tag4g_pair = [0]*len(sents_g_pair) #记录groudtruth中错误对被集中的次数  
		tag4g_single = [0]*len(sents_g_single) #记录groudtruth中单个错误被集中的次数  
		tag4p = [0]*len(p_sents)  #记录预测结果中和gd匹配上的次数  

		for j, sent_p in enumerate(p_sents):
			flag = False
			if len(sent_p) == 1:
				sent_p = sent_p[0].replace('\\n', '')
				for i, sent_g in enumerate(sents_g_single):
					if (sent_p in sent_g) or (sent_g in sent_p):
						tag4p[j] += 1
						tag4g_single[i] += 1
						flag = True
						break
				if flag:
					continue
				for i, sent_g in enumerate(sents_g_pair):
					if (sent_p in sent_g[0]) or (sent_g[0] in sent_p) or (sent_p in sent_g[1]) or (sent_g[1] in sent_p) :
						tag4p[j] += 1
						tag4g_pair[i] +=0.6
						break
			elif len(sent_p) > 2:
				print('error 最多只能输出一对sentences', sent_p, p_sents)   #按理说在前期提取结果时这种情况已经排除了
				print(fname)
			else:
				sent_p = [sent_p[0].replace('\\n', ''), sent_p[1].replace('\\n', '')]
				for i, sent_g in enumerate(sents_g_single):
					if (sent_p[0] in sent_g) or (sent_g in sent_p[0]) or (sent_p[1] in sent_g) or (sent_g in sent_p[1]):
						# print("sent_g:", sent_g )
						# print('sent_p:', sent_p)
						# print(j, i)
						tag4p[j] += 0.6
						tag4g_single[i] += 1
						flag = True
						break
				if flag:
					continue
				for i, sents_g in enumerate(sents_g_pair):
					if (sents_g[0] in sent_p[0]) or (sent_p[0] in sents_g[0]):
						if (sents_g[1] in sent_p[1]) or (sent_p[1] in sents_g[1]) or (sents_g[1] in sent_p[0]) or (sent_p[0] in sents_g[1]):
							tag4p[j] += 1
							tag4g_pair[i] += 1
							break
						else:
							tag4p[j] += 0.6   #只是为了区分，0.6不能凑整
							tag4g_pair[i] += 0.6
							#print('匹配上了一半:', fname, '\n---------sent_p\n', sent_p, '---------sent_g\n', sents_g)
							break

					elif (sents_g[0] in sent_p[1]) or (sent_p[1] in sents_g[0]):
						if (sents_g[1] in sent_p[1]) or (sent_p[1] in sents_g[1]) or (sents_g[1] in sent_p[0]) or (sent_p[0] in sents_g[1]):
							tag4p[j] += 1
							tag4g_pair[i] += 1
							break
						else:
							tag4p[j] += 0.6   #只是为了区分，0.6不能凑整
							tag4g_pair[i] += 0.6
							break

		# print('res: tag4g_pair:', json.dumps(tag4g_pair, ensure_ascii=False))
		# print('-----------\ntag4g_single:', json.dumps(tag4g_single, ensure_ascii=False))
		# print('-----------\ntag4p:', json.dumps(tag4p, ensure_ascii=False))

		count_g_p = sum(1 for num in tag4g_pair if num != 0)
		count_g_s = sum(1 for num in tag4g_single if num != 0)
		count_p = sum(1 for num in tag4p if num != 0)
		if count_g_s + count_g_p != count_p:
			print("error 两个结果不对等", count_g_s + count_g_p, count_p)
			print(tag4g_pair, tag4g_single)
			print(tag4p)
			print('gd:', json.dumps(gd_sents,ensure_ascii=False), '\n**************')
			print('pd:', json.dumps(p_sents, ensure_ascii=False))

		if count_p != len(tag4p):
			print(f'---------------\n当前处理的文件是{fname}')
			print('gd:', gd_sents)
			print('pd:', p_sents)
			print(tag4g_pair, tag4g_single)
			print(tag4p)
			print('sents_g_pair:', sents_g_pair)
			print('sents_g_single:', sents_g_single)
			print('标准答案中没被击中的:')
			for i in range(len(tag4g_pair)):
				if tag4g_pair[i] == 0:
					print(sents_g_pair[i])
			for i in range(len(tag4g_single)):
				if tag4g_single[i] == 0 :
					print([sents_g_single[i]])
			if not toge:
				print('多预测的结果:')
				for i in range(len(tag4p)):
					if tag4p[i] == 0:
						print(p_sents[i])
			print('匹配上的结果:')
			for i in range(len(tag4p)):
				if tag4p[i] != 0:
					print(p_sents[i])
		else:
			print('gd:', gd_sents)
			print('pd:', p_sents)			
		# self.tp += count_p
		self.tp += count_g_p+count_g_s
		self.fp += len(p_sents) - count_p
		self.fn += len(gd_sents) - count_g_p - count_g_s

	def extract_yes_or(self, output):
		#output: [[判断的候选, 返回结果] ]，格式:[[[], '']]
		res = []
		yes_pa = r'(^是)|((答案|结论|返回|回答|结果|判断|判定).{0,4}是)|(是”存在问题的)'

		no_pa = r'(^否)|((答案|回答|判断|判定|结论|结果|评估|返回|回复|回应|这里是).{0,6}否)'
		for info in output:
			error, q, a = info[0], info[1], info[2]
			a = a.replace("**", '').replace('“', '').replace('- ', '')
			sents = a.split('\n')
			flag = False
			for s in sents[::-1]:
				if not s:
					continue
			
				temp = re.search(no_pa, s)
				if temp:
					res.append(-1)
					flag = True
					break

				temp = re.search(yes_pa, s)
				if temp:
					res.append(1)
					flag = True
					break

				# print('尚未考虑到的情况', s)

			if not flag:	
				if "**否**" in info[2]:
					res.append(-1)
				elif '“是”' in info[2] or '【是】' in info[2]:
					res.append(1)
				elif '“否”' in info[2] or '【否】' in info[2]:
					res.append(-1)
				else:
					res.append('unknown')
					print('----------------\n尚未考虑到的情况', info[2])

		assert len(res) == len(output)	

		return res

def main_eval():
	#统计大模型漏洞检测的效果
	rator = Eval()
	rator.toge = False

	if '14b' in rator.llm:
		output_path = './output14'
	elif '32b' in rator.llm:
		output_path = './output32'
	elif '7b' in rator.llm:
		output_path = './output7'

	# output_path = './output'   #要改logic， 因为返回的是单维列表
	# output_path = './new_output'
	# # output_path = './chunk'
	# output_path = './judge_ouput1'
	# output_path = './judge_output'

	
	files = os.listdir(output_path)
	all_outputs = defaultdict(list)
	for f in files:
		if not f.startswith(rator.llm):
			continue

		print('当前处理的错误类型是：', f)
		fname = os.path.join(output_path, f)
		# if ('矛盾错误' in f) or ('逻辑错误' in f) :
		# 	logic = True
		# else:
		# 	logic = False
		logic = False
		all_outputs = rator.new_handle_file(fname, all_outputs, logic)

	print('all_outputs: ', json.dumps(all_outputs, ensure_ascii=False))
	all_outputs = json.dumps(all_outputs, ensure_ascii=False)
	all_outputs = all_outputs.replace(' ', '')
	all_outputs = json.loads(all_outputs)

	# names = list(all_outputs.keys())[:2]
	# temp_all_outputs = copy.deepcopy(all_outputs)
	# all_outputs = {names[0]: temp_all_outputs[names[0]], names[1]: temp_all_outputs[names[1]]}


	gd_path = './groundtruth'
	if rator.toge:   #所有错误一起统计
		gd_sents = {}
		for f in os.listdir(gd_path):
			if 'all_merge' not in f:
				continue
			f = os.path.join(gd_path, f)
			with open(f, 'r', encoding='utf-8') as fr:
				line = fr.readline()
				line = line.replace('　', ' ')
				while line:
					x = json.loads(line)
					gd_sents[x['id']] = x['sents']
					line = fr.readline()
					line = line.replace('　', ' ').replace(' ', '')

		print('-----------compare-------------')			
		rator.compare(all_outputs, gd_sents)
	else:
		for error_type in rator.error_types:
			print('当前处理的错误类型是：', error_type)
			rator.current_error = error_type
			rator.tp, rator.fp, rator.fn, rator.tn = 0,0,0,0
			gd_sents = {}
			gd_f = os.path.join(gd_path, error_type+'.json')
			with open(gd_f, 'r', encoding='utf-8') as fr:
				line = fr.readline()
				while line:
					x = json.loads(line)
					gd_sents[x['id']] = x['sents']
					line = fr.readline()
			print('-----------compare-------------')			
			rator.compare(all_outputs, gd_sents, rator.toge)			
			# break
	pre = round(rator.total_tp *1.0 /max(rator.total_tp +rator.total_fp, 1), 4)
	rec = round(rator.total_tp * 1.0 / max(rator.total_tp + rator.total_fn, 1), 4)
	if pre+rec == 0:
		f1 = round(2*pre*rec/1, 4)
	else:
		f1 = round(2*pre*rec/(pre+rec), 4)
	print(f"Pre: {pre}, Rec: {rec}, F1: {f1}")

	rator.scores['all'] = {'tp': rator.total_tp, 'fp': rator.total_fp, 'fn': rator.total_fn,
								'pre': pre, 'rec': rec, 'f1': f1}

	for error_type in rator.error_types:
		print(f"{error_type}, {rator.scores[error_type]['tp']}, {rator.scores[error_type]['fp']}, {rator.scores[error_type]['fn']}, {rator.scores[error_type]['pre']}, {rator.scores[error_type]['rec']}, {rator.scores[error_type]['f1']}")
	error_type = 'all'
	print(f"{error_type}, {rator.scores[error_type]['tp']}, {rator.scores[error_type]['fp']}, {rator.scores[error_type]['fn']}, {rator.scores[error_type]['pre']}, {rator.scores[error_type]['rec']}, {rator.scores[error_type]['f1']}")

		
def main_eval_judge():
	# output_path = './judge_output'
	output_path = './judge_ouput1'

	rator = Eval()

	file = os.path.join(output_path, 'judge_res_qwen2.5_32b_context.jsonl')
	with open(file, 'r', encoding='utf-8') as fr:
		data = json.load(fr)

	statistic = {}
	for x in data:
		name = x['name']
		llm_res = x['res']

		res = rator.extract_yes_or(llm_res)
		for i, temp in enumerate(res):
			error = llm_res[i][0]
			if error not in statistic:
				statistic[error] = {'tp':0, 'fn':0}
			if temp == 1:
				statistic[error]['tp'] += 1
			else:
				statistic[error]['fn'] += 1

	tp = 0
	fn = 0			
	for error, info in statistic.items():
		print(f"error: {error}, TP: {info['tp']}, FN: {info['fn']}, ACC: {round(info['tp']*1.0/(info['tp']+info['fn']), 4)}")	
		tp += info['tp']
		fn += info['fn']
	print(F'all: TP:{tp}, FN:{fn}, ACC: {round(tp*1.0/(tp+fn), 4)}')

def main_eval_gpt():
	rator = Eval()
	# rator.toge = False
	doc_file = './output/qwen2.5_32b_计算错误_res.jsonl'
	target_fnames = []
	with open(doc_file, 'r', encoding='utf-8') as fr:
		data = json.load(fr)
		for x in data:
			name = x['name']
			target_fnames.append(name)

	print(json.dumps(target_fnames, ensure_ascii=False))


	gd_path = './groundtruth'

	
	all_outputs = defaultdict(list)
	gd_sents = {}

	print('target_fnames:', target_fnames)
	res_path = '../analysis_zhecheng/output'
	for f in os.listdir(res_path):
		f = os.path.join(res_path, f)
		with open(f, 'r', encoding='utf-8') as fr:
			line = fr.readline()
			while line:
				x = json.loads(line)
				fname = x['id']
				if fname not in target_fnames:
					line = fr.readline()
					continue
				res = x['sents']
				for x in res:
					flag = False
					if len(x) == 1:
						for i, y in enumerate(all_outputs[fname]):
							if len(y) != 1:
								continue
							else:
								try:
									if x[0] in y[0]:
										flag = True
										break
									elif y[0] in x[0]:
										all_outputs[fname][i][0] = x[0]
										flag = True
										break
								except:
									traceback.print_exc()
									print(x, y)
					elif len(x) == 2:
						for i,y in enumerate(all_outputs[fname]):
							if len(y) != 2:
								continue
							else:
								if (x[0] in y[0]) or (y[0] in x[0]):
									if (x[1] in y[1]) or (y[1] in x[1]):
										flag = True
										break
								elif (y[0] in x[1]) or (x[1] in y[0]):
									if (x[0] in y[1]) or (y[1] in x[0]):
										flag = True
										break
					else:
						print('不该不出现的结果', x)	
					if not flag:		
						all_outputs[fname].append(x)
				#all_outputs[fname].extend(res)
				line = fr.readline()



	assert len(all_outputs.keys()) == 50
	print('predict阅读结束')			
	if rator.toge:
		for f in os.listdir(gd_path):
			if 'merge' not in f:
				continue
			f = os.path.join(gd_path, f)
			with open(f, 'r', encoding='utf-8') as fr:
				line = fr.readline()
				while line:
					x = json.loads(line)
					gd_sents[x['id']] = x['sents']
					line = fr.readline()

		rator.compare(all_outputs, gd_sents)
	else:
		for error_type in rator.error_types:
			print('当前处理的错误类型是：', error_type)
			rator.tp, rator.fp, rator.fn, rator.tn = 0,0,0,0
			gd_sents = {}
			gd_f = os.path.join(gd_path, error_type+'.json')
			with open(gd_f, 'r', encoding='utf-8') as fr:
				line = fr.readline()
				while line:
					x = json.loads(line)
					gd_sents[x['id']] = x['sents']
					line = fr.readline()
			rator.compare(all_outputs, gd_sents, rator.toge)

def main_eval_compition():
	rator = Eval()
	rator.toge = False
	doc_file = './output/qwen2.5_32b_计算错误_res.jsonl'
	target_fnames = []
	with open(doc_file, 'r', encoding='utf-8') as fr:
		data = json.load(fr)
		for x in data:
			name = x['name']
			target_fnames.append(name)

	print(json.dumps(target_fnames, ensure_ascii=False))


	gd_path = './groundtruth'

	
	all_outputs = defaultdict(list)
	gd_sents = {}

	print('target_fnames:', target_fnames)
	res_path = '../analysis_zhecheng/output'
	for f in os.listdir(res_path):
		f = os.path.join(res_path, f)
		with open(f, 'r', encoding='utf-8') as fr:
			line = fr.readline()
			while line:
				x = json.loads(line)
				fname = x['id']
				if fname not in target_fnames:
					line = fr.readline()
					continue
				res = x['sents']
				for x in res:
					flag = False
					if len(x) == 1:
						for i, y in enumerate(all_outputs[fname]):
							if len(y) != 1:
								continue
							else:
								try:
									if x[0] in y[0]:
										flag = True
										break
									elif y[0] in x[0]:
										all_outputs[fname][i][0] = x[0]
										flag = True
										break
								except:
									traceback.print_exc()
									print(x, y)
					elif len(x) == 2:
						for i,y in enumerate(all_outputs[fname]):
							if len(y) != 2:
								continue
							else:
								if (x[0] in y[0]) or (y[0] in x[0]):
									if (x[1] in y[1]) or (y[1] in x[1]):
										flag = True
										break
								elif (y[0] in x[1]) or (x[1] in y[0]):
									if (x[0] in y[1]) or (y[1] in x[0]):
										flag = True
										break
					else:
						print('不该不出现的结果', x)	
					if not flag:		
						all_outputs[fname].append(x)
				#all_outputs[fname].extend(res)
				line = fr.readline()

	

	assert len(all_outputs.keys()) == 50
	print('predict阅读结束')			
	if rator.toge:
		for f in os.listdir(gd_path):
			if 'merge' not in f:
				continue
			f = os.path.join(gd_path, f)
			with open(f, 'r', encoding='utf-8') as fr:
				line = fr.readline()
				while line:
					x = json.loads(line)
					gd_sents[x['id']] = x['sents']
					line = fr.readline()

		rator.compare(all_outputs, gd_sents)
	else:
		for error_type in rator.error_types:
			print('当前处理的错误类型是：', error_type)
			rator.tp, rator.fp, rator.fn, rator.tn = 0,0,0,0
			gd_sents = {}
			gd_f = os.path.join(gd_path, error_type+'.json')
			with open(gd_f, 'r', encoding='utf-8') as fr:
				line = fr.readline()
				while line:
					x = json.loads(line)
					gd_sents[x['id']] = x['sents']
					line = fr.readline()
			rator.compare(all_outputs, gd_sents, rator.toge)

def main_eva_tgea(): 
	file = 'tgea_judge_res_qwen2.5_32b.json'   #错误的是-1， 正确的是1
	yes_pa = r'(^是)|((答案|结论|返回|回答|结果|判断|判定).{0,4}是)|(是”存在问题的)'
	no_pa = r'(^否)|((答案|回答|判断|判定|结论|结果|评估|返回|回复|回应|这里是).{0,6}否)'

	yes_tp = 0
	yes_fn = 0  #错误分类为负样本
	no_tn = 0
	no_fp = 0   #错误分类为正样本
	with open(file, 'r', encoding='utf-8') as fr:
		data = json.load(fr)
		for i, x in enumerate(data):   # text, tag, error, pre
			text, tag, error, pred = x

			res = re.search(no_pa, pred)
			if res:
				if tag != 1:
					data[i].append(False)
					print('fp: ', data[i])
					no_fp += 1
					continue
				else:
					data[i].append(True)
					no_tn += 1
					continue
			res = re.search(yes_pa, pred)
			if res:
				if tag != -1:
					data[i].append(False)
					print('fn:', data[i])
					yes_fn += 1
					continue
				else:
					data[i].append(True)
					yes_tp += 1
					continue

			data[i].append('unknown')
			if tag == 1:
				yes_fn += 1
			else:
				no_fp += 1

	print(f'yes_tp: {yes_tp}, yes_fn: {yes_fn}, no_tn: {no_tn}, no_fp: {no_fp}, acc:{round((yes_tp+no_tn)*1.0/(yes_tp+yes_fn+no_tn+no_fp), 4)}')

def main_eva_single_error():
	#一次只检测一个错误
	#统计大模型漏洞检测的效果
	rator = Eval()
	rator.toge = False

	if '14b' in rator.llm:
		output_path = './output14'
		output_path = './answers'
	elif '32b' in rator.llm:
		output_path = './output32'
	elif '7b' in rator.llm:
		output_path = './output7'

	gd_path = './groundtruth'	
	# rator.error_types = ['语句缺失错误']
	# rator.error_types = ['格式错误']
	for error_type in rator.error_types:
		print('当前处理的错误类型是：', error_type)
		rator.current_error = error_type
		fname = os.path.join(output_path, rator.llm+'_'+error_type+'_res.jsonl')
		temp_res = defaultdict(list)
		all_outputs = rator.new_handle_file(fname, temp_res, logic=False)

		all_outputs = json.dumps(all_outputs, ensure_ascii=False)
		all_outputs = all_outputs.replace(' ', '')
		try:
			all_outputs = json.loads(all_outputs)
		except:
			traceback.print_exc()
			print(all_outputs)
			exit()
		print('all_outputs: ', json.dumps(all_outputs, ensure_ascii=False))

		gd_sents = {}
		f = os.path.join(gd_path, error_type+'.json')
		with open(f, 'r', encoding='utf-8') as fr:
			line = fr.readline()
			while line:
				line = line.replace('　', ' ').replace(' ', '').replace('\n', '')
				x = json.loads(line)
				gd_sents[x['id']] = x['sents']
				line = fr.readline()

		print('-----------compare-------------')			
		rator.compare(all_outputs, gd_sents)
		if not rator.toge:
			rator.fp = 0
			rator.tp = 0
			rator.fn = 0
			rator.tn = 0
		# break

	pre = round(rator.total_tp *100 /max(rator.total_tp +rator.total_fp, 1), 2)
	rec = round(rator.total_tp * 100 / max(rator.total_tp + rator.total_fn, 1), 2)
	if pre+rec == 0:
		f1 = round(2*pre*rec/1, 2)
	else:
		f1 = round(2*pre*rec/(pre+rec), 2)
	print(f"Pre: {pre}, Rec: {rec}, F1: {f1}")

	rator.scores['all'] = {'tp': rator.total_tp, 'fp': rator.total_fp, 'fn': rator.total_fn,
								'pre': pre, 'rec': rec, 'f1': f1}

	for error_type in rator.error_types:
		print(f"{error_type}, {rator.scores[error_type]['tp']}, {rator.scores[error_type]['fp']}, {rator.scores[error_type]['fn']}, {rator.scores[error_type]['pre']}, {rator.scores[error_type]['rec']}, {rator.scores[error_type]['f1']}")
	error_type = 'all'
	print(f"{error_type}, {rator.scores[error_type]['tp']}, {rator.scores[error_type]['fp']}, {rator.scores[error_type]['fn']}, {rator.scores[error_type]['pre']}, {rator.scores[error_type]['rec']}, {rator.scores[error_type]['f1']}")

if __name__ == '__main__':
	main_eva_single_error()
	exit()
	# main_eva_tgea()
	# exit()
	# main_eval_judge()
	main_eval()
	# main_eval_gpt()