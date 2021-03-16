# local staging (requires a local nginx service running)
stage-local:
	rm -r ./dist
	npm run-script build -- --env.appMode=private
	cp -r dist ~/nginx/data/dist

# the internal public deployment (for now, on `hulk`)
deploy-hulk:
	rm -r ./dist
	npm run-script build -- --env.appMode=public
	scp -r dist keith@cap:/gpfs/gpfsML/ML_group/KC/nginx/hulk/data/

# the internal private deployment on `cap`
deploy-cap:
	rm -r ./dist
	npm run-script build -- --env.appMode=private
	scp -r dist keith@cap:/gpfs/gpfsML/ML_group/KC/nginx/data/

# the public deployment on AWS
deploy-aws:
	rm -r ./dist
	npm run-script build -- --env.appMode=public
	scp -i ~/aws/keith-cheveralls-rsa -r dist/ ubuntu@ec2-44-230-211-234.us-west-2.compute.amazonaws.com:/home/ubuntu/data

