#!/usr/bin/env python
import sys, os, json, cStringIO, tempfile, logging, traceback, codecs, math
import textprocessor
from lib.porter2 import stem

class WordCloud(textprocessor.TextProcessor):
	"""
	Generate word cloud
	"""
	def _basic_params(self):
		self.name = "wordcloud"
		self.width = "300"
		self.height = "150"
		self.fontsize = "[10,32]"
		self.n = 50
		self.tfidf_scoring = False

	def _findTfIdfScores(self, scale=True):
		self.freqs = {}
		self.tf_by_doc = {}
		self.max_tf = {}
		self.df = {}
		for filename in self.files:
			with codecs.open(filename, 'r', encoding = 'utf8') as f:
				logging.info("processing " + filename)
				flen = 0
				self.tf_by_doc[filename] = {}
				for line in f:
					for stem in self._tokenizeAndStem(line):
						flen += 1
						if stem not in self.tf_by_doc[filename]:
							self.tf_by_doc[filename][stem] = 0
							if stem not in self.df:
								self.df[stem] = 0
							self.df[stem] += 1
						self.tf_by_doc[filename][stem] += 1
				# max_tf_d = max(self.tf_by_doc[filename].values())
				for stem in self.tf_by_doc[filename].keys():
					if stem not in self.freqs:
						self.freqs[stem] = 0
					self.freqs[stem] += self.tf_by_doc[filename][stem]
					if scale:
						self.tf_by_doc[filename][stem] /= float(flen) #max_tf_d
						this_tf = self.tf_by_doc[filename][stem]
					else:
						this_tf = self.tf_by_doc[filename][stem] / float(flen)

					if stem not in self.max_tf or self.max_tf[stem] < this_tf:
						self.max_tf[stem] = this_tf
				self.update_progress()
		n = float(len(self.files))
		self.idf = {term: math.log10(n/df) for term, df in self.df.iteritems()}
		self.tfidf = {term: self.max_tf[term] * self.idf[term] for term in self.max_tf.keys()}
		tfidf_values = self.tfidf.values()
		top_terms = min(int(len(self.freqs.keys()) * 0.7), 5000)
		min_score = sorted(tfidf_values, reverse=True)[min(top_terms, len(tfidf_values) - 1)]
		self.filtered_freqs = {term: freq for term, freq in self.freqs.iteritems() if self.tfidf[term] > min_score and self.df[term] > 3}

	def _topN(self, freqs, n = None):
		if n is None:
			n = self.n
		final_freqs = []
		top_freqs = sorted(freqs.values())
		if len(top_freqs) == 0:
			return []
		min_freq = top_freqs[-min(n,len(top_freqs))] # find nth frequency from end, or start of list
		for word, freq in freqs.iteritems():
			if freq >= min_freq:
				final_freqs.append({'text': word, 'value': freq})
		return final_freqs

	def _findWordFreqs(self, filenames):
		freqs = {}
		for filename in filenames:
			with codecs.open(filename, 'r', encoding = 'utf8') as f:
				logging.info("processing " + filename)
				for line in f:
					for stem in self._tokenizeAndStem(line):
						if stem not in freqs:
							freqs[stem] = 1
						else:
							freqs[stem] += 1
			self.update_progress()
		return self._topN(freqs)

	def _tokenizeAndStem(self, line):
		# uncomment for Porter stemming (slower, but groups words with their plurals, etc.)
		# return [stem(word.strip('.,')) for word in line.split() if word.lower() not in self.stopwords and len(word) > 3]
		return [word.lower() for word in line.split() if word.lower() not in self.stopwords and word.isalpha() and len(word) >= 3]

	def process(self):
		logging.info("starting to process")

		self.template_filename = os.path.join(self.cwd, "templates", "wordcloud.html")

		logging.info("finding word frequencies")

		if self.tfidf_scoring:
			self._findTfIdfScores()
			freqs = self._topN(self.filtered_freqs)
		else:
			freqs = self._findWordFreqs(self.files)

		params = {"DATA": json.dumps(freqs),
				"WIDTH": self.width,
				"HEIGHT": self.height,
				"FONTSIZE": self.fontsize
		}

		self.write_html(params)


if __name__ == "__main__":
	try:
		processor = WordCloud(track_progress = True)
		processor.process()
	except:
		logging.error(traceback.format_exc())