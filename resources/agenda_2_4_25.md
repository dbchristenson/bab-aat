Detections
	- Collect ALL detections even non-tagged ones
	- 3/4/25 FEATURE COMPLETE, STABILITY TESTING STILL REQUIRED

Annotating
	- Setup portable tagging service
	- Arrange documents of interest for tagging
	- Train someone to tag and let them go

Evaluation
	- Design new DB models for storing evaluation data
	- Basically we have detections table and truth table
		- For each truth entry, we search the detection table for a match
		- Fuzzy matching? remove white-space to clean up entries?
		- We see how many tags we missed
	- Metrics to calculate
		- Recall -> TP / TP + FP
			- Denominator is effectively len(truth_table) for each doc
		- Maybe F2, we will see

Refining
	- Hyperparameter tuning? How to implement
	- How are we gonna track models and training runs