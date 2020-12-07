help:
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

create-vyked-logs: ## Run to create log files for vyked
	mkdir logs
	touch logs/vyked_exceptions.log

run-vyked: ## Run vyked
	python3 -m vyked.registry