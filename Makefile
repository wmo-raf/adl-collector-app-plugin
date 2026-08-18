# Run against this repo's own compose stack (docker compose up), which already
# dev-installs the plugin into the adl container. SimpleTestCase does not make
# the suite runnable outside the stack: Django's runner calls setup_databases()
# unconditionally whatever the test class.
test:
	docker compose exec adl adl test --keepdb adl_collector_app_plugin.tests

lint:
	$(MAKE) -C plugins/adl_collector_app_plugin lint

format:
	$(MAKE) -C plugins/adl_collector_app_plugin format
