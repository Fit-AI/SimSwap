all: simswap

environment:
ifndef SUPABASE_KEY
	$(error SUPABASE_KEY is undefined)
endif
ifndef SUPABASE_URL
	$(error SUPABASE_URL is undefined)
endif

simswap: environment
	docker build -t gcr.io/savvy-webbing-347620/simswap-api-vertex:latest \
				 --build-arg SUPABASE_URL_ARG=${SUPABASE_URL} 	\
				 --build-arg SUPABASE_KEY_ARG=${SUPABASE_KEY} 	\
				 .

install: simswap
	docker push gcr.io/savvy-webbing-347620/simswap-api-vertex:latest
