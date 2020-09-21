
stage:
	rm -r ./dist
	npm run-script build
	scp -r dist keith@cap:/gpfs/gpfsML/ML_group/KC/nginx/hulk/data/

deploy:
	rm -r ./dist
	npm run-script build
	scp -r dist keith@cap:/gpfs/gpfsML/ML_group/KC/nginx/data/