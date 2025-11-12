from typing import Type, TypeVar

T = TypeVar('T', bound='Renewable')


class Renewable:

    @classmethod
    def renew(cls: Type[T], old_instance: T) -> T:
        """
        Creates a new instance by copying all defined (annotated) attributes from the old instance.
        """
        annotations = {}
        for base in reversed(cls.__mro__):
            annotations.update(getattr(base, '__annotations__', {}))

        kwargs = {}
        for attr in annotations:
            if hasattr(old_instance, attr):
                kwargs[attr] = getattr(old_instance, attr)
            else:
                kwargs[attr] = getattr(cls, attr, None)

        return cls(**kwargs)
