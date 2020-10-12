# staging locally (requires local nginx service)
stage-local:
	rm -r ./dist
	npm run-script build -- --env.APP_MODE=private
	cp -r dist ~/nginx/data/dist

# staging on `hulk`
stage:
	rm -r ./dist
	npm run-script build -- --env.APP_MODE=private
	scp -r dist keith@cap:/gpfs/gpfsML/ML_group/KC/nginx/hulk/data/

# the internal ('private') deployment on `cap`
deploy-internal:
	rm -r ./dist
	npm run-script build -- --env.APP_MODE=private
	scp -r dist keith@cap:/gpfs/gpfsML/ML_group/KC/nginx/data/

# the public deployment on AWS
# TODO: copy ./dist to AWS
deploy-aws:
	rm -r ./dist
	npm run-script build -- --env.APP_MODE=public
