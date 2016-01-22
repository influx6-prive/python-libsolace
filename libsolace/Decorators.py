import logging
from libsolace.util import get_calling_module


def only_on_shutdown(entity):
    def wrap(f):
        def wrapped_f(*args, **kwargs):
            mode = kwargs.get('shutdown_on_apply', None)
            if entity == 'queue' and mode in ['b', 'q', True]:
                return f(*args, **kwargs)
            if entity == 'user' and mode in ['b', 'u', True]:
                return f(*args, **kwargs)
            module = get_calling_module()
            logging.info("Calling package %s - Shutdown on apply is not enabled, bypassing %s for entity %s" % (
                module, f.__name__, entity))

        return wrapped_f

    return wrap


def only_if_not_exists(entity, data_path, primaryOnly=False, backupOnly=False):
    """
    Return METHOD if the item does NOT exist in the Solace appliance.

    if the object's exists caching bit is False, return the method
    If the object does not exist, return the method and set the exists bit to False
    If the object exists in the appliance, set the exists bit to True

    :param entity: the "getter" to call
    :param data_path: a dot name spaced string which will be used to decend into the response document to verify exist
    :param primaryOnly: run the "getter" only against primary
    :param backupOnly: run the "getter" only against backup
    :return:
    """

    def wrap(f):
        def wrapped_f(*args, **kwargs):

            # default false
            check_primary = False
            check_backup = False

            # extract package name
            module = get_calling_module()

            # determine if were checking both or a single node
            if primaryOnly:
                kwargs['primaryOnly'] = primaryOnly
                check_primary = True
            elif backupOnly and not primaryOnly:
                kwargs['backupOnly'] = backupOnly
                check_backup = True
            else:
                logging.info("Both primary and backup will be queried")
                check_primary = True
                check_backup = True

            # if exists bit is set on the object ( caching )
            try:
                if not args[0].exists:
                    logging.debug("Cache hit")
                    return f(*args, **kwargs)
            except Exception, e:
                pass

            logging.debug("Cache miss")

            logging.info("Calling package: %s, asking entity: %s, for args: %s, kwargs: %s via data_path: %s" % (
                module, entity, str(args), str(kwargs), data_path))

            response_path = data_path.split('.')

            res = getattr(args[0], entity)(**kwargs)
            logging.info("Response %s" % res)

            # try peek into attributes, any raises means one of the nodes does not have the object.
            o_res = res

            for p in response_path:
                if check_primary:
                    try:
                        res[0] = res[0][p]
                    except (TypeError, IndexError):
                        logging.info("Object not found on PRIMARY, key:%s error" % p)
                        logging.info(o_res)
                        kwargs['primaryOnly'] = True
                        args[0].set_exists(False)
                        return f(*args, **kwargs)
                if check_backup:
                    try:
                        res[1] = res[1][p]
                    except (TypeError, IndexError):
                        logging.info("Object not found on BACKUP, key:%s error" % p)
                        logging.info(o_res)
                        kwargs['backupOnly'] = True
                        args[0].set_exists(False)
                        return f(*args, **kwargs)

            # if we reach here, the object exists
            logging.info(
                    "Calling package %s - %s exists, ignoring creation" % (module, f.__name__))
            args[0].set_exists(True)

        return wrapped_f

    return wrap


def only_if_exists(entity, data_path, primaryOnly=False, backupOnly=False):
    """
    If object exists bit set, return the method
    If object exists bit not set, query the object, return the method if succes
    If object does not exist, dont return the method.

    :param entity: the "getter" to call
    :param data_path: a dot name spaced string which will be used to decend into the response document to verify exist
    :param primaryOnly: run the "getter" only against primary
    :param backupOnly: run the "getter" only against backup
    :return:
    """

    def wrap(f):
        def wrapped_f(*args, **kwargs):

            # default false
            check_primary = False
            check_backup = False

            # extract package name
            module = get_calling_module()

            # determine if were checking both or a single node
            if primaryOnly:
                kwargs['primaryOnly'] = primaryOnly
                check_primary = True
            elif backupOnly and not primaryOnly:
                kwargs['backupOnly'] = backupOnly
                check_backup = True
            else:
                logging.info("Both primary and backup will be queried")
                check_primary = True
                check_backup = True

            # if exists bit is set on the object ( caching )
            try:
                if args[0].exists:
                    logging.debug("Cache hit")
                    return f(*args, **kwargs)
            except Exception, e:
                pass

            logging.debug("Cache miss")
            logging.info("Calling package: %s, asking entity: %s, for args: %s, kwargs: %s via data_path: %s" % (
                module, entity, str(args), str(kwargs), data_path))

            response_path = data_path.split('.')

            res = getattr(args[0], entity)(**kwargs)
            o_res = res
            logging.debug("Response %s" % res)

            # try peek into attributes, any raises means one of the nodes does not have the object.
            for p in response_path:
                if check_primary:
                    try:
                        res[0] = res[0][p]
                    except (TypeError, IndexError):
                        logging.info("Object not found on PRIMARY, key:%s error" % p)
                        logging.info(o_res)
                        kwargs['primaryOnly'] = True
                        args[0].set_exists(False)
                if check_backup:
                    try:
                        res[1] = res[1][p]
                    except (TypeError, IndexError):
                        logging.info("Object not found on BACKUP, key:%s error" % p)
                        logging.info(o_res)
                        kwargs['backupOnly'] = True
                        args[0].set_exists(False)

            module = get_calling_module()
            logging.info(
                    "Calling package %s - Object exists, calling method %s, check entity was: %s" % (module, f.__name__, entity))
            args[0].set_exists(True)
            return f(*args, **kwargs)

        return wrapped_f

    return wrap


def primary():
    """
    Set the primaryOnly kwarg, call the method

    :return:
    """
    def wrap(f):
        def wrapped_f(*args, **kwargs):
            kwargs['primaryOnly'] = True
            module = get_calling_module()
            logging.info("Calling package %s - Setting primaryOnly: %s" % (module, f.__name__))
            return f(*args, **kwargs)

        return wrapped_f

    return wrap


def backup():
    """
    Set the backupOnly kwarg, call the method

    :return:
    """
    def wrap(f):
        def wrapped_f(*args, **kwargs):
            kwargs['backupOnly'] = True
            module = get_calling_module()
            logging.info("Calling package %s - Setting backupOnly: %s" % (module, f.__name__))
            return f(*args, **kwargs)

        return wrapped_f

    return wrap